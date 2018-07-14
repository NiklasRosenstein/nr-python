# Copyright (c) 2018 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

from nr.stream import stream
from .utils import system
from .hooks import Hook

import ast
import copy
import itertools
import logging
import nr.fs
import nr.types
import os
import sys
import sysconfig


def get_native_suffixes():
  """
  Returns a list of the suffixes used by Python C-Extensions.
  """

  # NOTE: Do we need to use PEP425 to determine the SO suffix on Windows?
  #       Does sysnconfig["SO"] not contain the *one* suffix that is used?
  #if system.is_win and not system.is_unix:
  #  try:
  #    import pip._internal.pep425tags as tags
  #  except ImportError:
  #    import pip.pep425tags as tags
  #  return ['.pyd', '.' + tags.implementation_tag + '-' + tags.get_platform() + '.pyd']
  #else:
  return [sysconfig.get_config_var('SO')]


def get_imports(filename, source=None):
  """
  Returns a list of #ImportInfo tuples for all module imports in the specified
  Python source file or the *source* string. Note that `from X import Y`
  imports could also refer to a member of the module X named Y and not the
  module X.Y.
  """

  def _find_nodes(ast_node, predicate):
    result = []
    class Visitor(ast.NodeVisitor):
      def visit(self, node):
        if predicate(node):
          result.append(node)
        self.generic_visit(node)
    Visitor().generic_visit(ast_node)
    return result

  if source is None:
    with open(filename, 'rb') as fp:
      source = fp.read()

  module = ast.parse(source, filename)
  result = []

  for node in _find_nodes(module, lambda x: isinstance(x, ast.Import)):
    for alias in node.names:
      result.append(ImportInfo(alias.name, filename, node.lineno, False))
  for node in _find_nodes(module, lambda x: isinstance(x, ast.ImportFrom)):
    parent_name = '.' * node.level + (node.module or '')
    result.append(ImportInfo(parent_name, filename, node.lineno, False))
    for alias in node.names:
      if alias.name == '*': continue
      import_name = parent_name
      if not import_name.endswith('.'):
        import_name += '.'
      import_name += alias.name
      result.append(ImportInfo(import_name, filename, node.lineno, True))

  result.sort(key=lambda x: x.lineno)
  return result


class ImportInfo(nr.types.Named):
  __annotations__ = [
    ('name', str),
    ('filename', str),
    ('lineno', int),
    ('is_from_import', bool)
  ]

  @property
  def parent(self):
    if self.name == '.' or self.name.count('.') == 0:
      return None
    result = copy.copy(self)
    result.name = self.name.rpartition('.')[0]
    return result

  def is_abs(self):
    return not self.name.startswith('.')

  def to_abs(self, parent_module):
    """
    If *self* represents an absolute import, a copy will be returned.
    Otherwise, the relative module spec will be converted to an absolute
    module name using the specified *parent_module*.

    If *parent_module* is a #ModuleInfo object, the relative import will
    be treated properly depending on whether the module is the root of a
    package or not.

    Alternatively, if *parent_module* is a string, it will be treated as
    if it was the root of a package.

    For a root package, the full package name will be used when resolving
    the relative module spec. For submodules, the parent package name will
    be used for resolving the module spec.

    Examples:

        parent_module: pkg_a.bar
        module spec: .foo
        result: pkg_a.bar.foo

        parent_module: pkg_a.bar (as a submodule)
        module spec: .foo
        result: pkg_a.foo
    """

    if isinstance(parent_module, ModuleInfo):
      if parent_module.is_submodule():
        parent_module = parent_module.parent_name
      else:
        parent_module = parent_module.name

    if not isinstance(parent_module, str):
      raise TypeError('parent_module: expected str or ModuleInfo, got {}'
        .format(type(parent_module).__name__))

    if self.is_abs():
      return copy.copy(self)

    level = sum(1 for _ in itertools.takewhile(lambda x: x == '.', self.name))
    if level == 0:
      module_name = self.name
    elif level == 1:
      submodule = self.name.lstrip('.')
      if submodule:
        module_name = parent_module + '.' + submodule
      else:
        module_name = parent_module
    else:
      prefix = '.'.join(parent_module.split('.')[:-level+1])
      if not prefix:
        raise ValueError('import {!r} from {!r} is invalid'.format(
          self.name, parent_module))
      module_name = prefix
      if len(self.name) > level:
        module_name += '.' + self.name[level:]


    return ImportInfo(module_name, self.filename, self.lineno, self.is_from_import)


class ModuleInfo(nr.types.Named):
  """
  Represents a Python module.
  """

  __annotations__ = [
    ('name', str),
    ('filename', str),
    ('type', type),
    ('imported_from', set, lambda: set()),
    ('imports', list, None),
    ('is_zippable', bool, None),
    ('graph', 'ModuleGraph', None),
    ('handled', bool, False),
    ('sparse', bool, None),
    ('package_data', list, lambda: []),
    ('native_deps', list, lambda: []),
  ]

  SRC = 'src'
  NATIVE = 'native'
  BUILTIN = 'builtin'
  NOTFOUND = 'notfound'

  def is_pkg(self):
    """
    Returns #True if this module appears to represent a Python package.
    """

    if self.type == self.SRC:
      return nr.fs.base(self.filename) == '__init__.py'
    for child in self.children:
      return True
    return False

  def is_root(self):
    """
    Returns #True if this module appars to be a root Python module or package.
    """

    return self.name.count('.') == 0

  def is_submodule(self):
    """
    Returns #True if this module appears to be a submodule.
    """

    return not (self.is_root() or self.is_pkg())

  @property
  def is_zippable(self):
    """
    Returns True if the module is zippable. If note defined in this
    #ModuleInfo object, its parent module will be checked which must
    me in the *modules* dictionary. If it is not defined on a root module,
    it will fall back to True.
    """

    if self._zippable is not None:
      return self._zippable
    if self.parent:
      return self.parent.zippable

  @is_zippable.setter
  def is_zippable(self, value):
    self._zippable = is_zippable

  @property
  def sparse(self):
    if self._sparse is not None:
      return self._sparse
    parent = self.parent
    if parent:
      return parent.sparse
    else:
      return self.graph.sparse

  @sparse.setter
  def sparse(self, value):
    self._sparse = value

  @property
  def parent(self):
    name = self.parent_name
    if name:
      return self.graph[name]
    return None

  @property
  def children(self):
    prefix = self.name + '.'
    count = prefix.count('.')
    for mod in self.graph:
      if mod.name.startswith(prefix) and mod.name.count('.') == count:
        yield mod

  @property
  def parent_name(self):
    """
    Returns the name of the parent module or #None if the module has no parent.
    """

    if self.name.count('.') == 0:
      return None
    return self.name.rpartition('.')[0]

  @property
  def relative_filename(self):
    """
    Returns the filename of the module relative to a modules directory.
    """

    if not self.filename:
      return None
    parts = self.name.split('.')
    parent = os.path.join(*parts[:-1]) if len(parts) > 1 else ''
    if self.type == self.SRC:
      if self.is_pkg():
        return os.path.join(parent, parts[-1], '__init__.py')
      else:
        return os.path.join(parent, parts[-1] + '.py')
    elif self.filename:
      return os.path.join(parent, os.path.basename(self.filename))
    else:
      raise ValueError('can not determine relative_filename of NOTFOUND module')

  @property
  def relative_directory(self):
    """
    Returns the directory of the module relative to a modules directory.
    """

    return os.path.dirname(self.relative_filename)

  @property
  def directory(self):
    """
    Returns the parent directory of the module or #None if the module
    was not found.
    """

    if self.filename is not None:
      return os.path.dirname(self.filename)
    return None

  def load_imports(self):
    self.imports = []
    if self.type != self.SRC:
      return

    try:
      imports = get_imports(self.filename)
    except SyntaxError as e:
      self.graph.logger.warn(
        'Unable to parse imports of module {} ({!r}): {}'
        .format(self.name, self.filename, e))
      return

    for imp in imports:
      imp = imp.to_abs(self)
      if imp.is_from_import:
        assert imp.parent, imp
        self.imports.append(imp.parent.name)
      self.imports.append(imp.name)

  def strip_imports(self, module_name):
    result = []
    prefix = module_name + '.'
    for name in self.imports:
      if not (name == module_name or name.startswith(prefix)):
        result.append(name)
    self.imports = result


class ModuleFinder(object):
  """
  This class implements finding Python modules by name in a search path.
  It does not implement caching the found modules, use the #ModuleGraph
  for that.
  """

  def __init__(self, path=None, native_suffixes=None):
    self.path = path or sys.path
    self.native_suffixes = native_suffixes or get_native_suffixes()

  def _try_module_at_path(self, path, module_name):
    # TODO: Add configurable behaviour for Python 2 where __init__.py is
    #       required and namespace packages are not automatically
    #       supported.
    parts = module_name.split('.')
    basename = os.path.join(path, *parts)
    kind = self._get_module_type(basename + '.py')
    if kind is not None:
      return ModuleInfo(module_name, basename + '.py', kind)
    kind = self._get_module_type(os.path.join(basename, '__init__.py'))
    if kind:
      return ModuleInfo(module_name, os.path.join(basename, '__init__.py'), kind)
    for suffix in self.native_suffixes:
      kind = self._get_module_type(basename + suffix)
      if kind:
        return ModuleInfo(module_name, basename + suffix, kind)
    return None

  def _get_module_type(self, filename):
    if not nr.fs.isfile_cs(filename):
      return None
    if filename.endswith('.py'):
      return ModuleInfo.SRC
    for suffix in self.native_suffixes:
      if filename.endswith(suffix):
        return ModuleInfo.NATIVE
    return None

  def find_module(self, module_name):
    """
    Attempts to find the module specified by *module_name* in the
    ModuleFinder's search path and returns a #ModuleInfo object.

    For builtin modules, the #ModuleInfo.filename will be None. Note that
    the #ModuleInfo.imported_from is not filled by this method. It is used
    with #ModuleFinder.iter_modules().
    """

    if module_name in sys.builtin_module_names:
      module = ModuleInfo(module_name, None, 'builtin')
    else:
      parts = module_name.split('.')
      module = None
      for dirname in self.path:
        module = self._try_module_at_path(dirname, module_name)
        if module:
          break
      else:
        module = ModuleInfo(module_name, None, ModuleInfo.NOTFOUND)

    return module

  def iter_package_modules(self, module, recursive=True):
    """
    Iterates over the submodules of the specified *module*. The modules
    found this way are added to the #modules dictionary but are marked as
    being found unnaturally.
    """

    if sys.version_info[0] == 2:
      if not module.is_pkg():
        return; yield
      # In Python 2, we need to find at least one package. Namespace
      # packages are then declared as such inside on of the __init__.py
      # files.
    else:
      # In Python 3, we do want to consider packages that have not been
      # found as they may refer to namespace packages.
      if module.type != module.NOTFOUND and not module.is_pkg():
        return; yield

    # The same module may appear mulitple times, for example when the
    # same directory is in the path twice.
    seen = set()
    for dirname in self.path:
      dirname = nr.fs.join(dirname, *module.name.split('.'))
      for name in nr.fs.listdir(dirname, do_raise=False):
        name = os.path.splitext(name)[0]
        if name == '__init__':
          continue
        import_name = module.name + '.' + name
        if import_name in seen:
          continue
        submodule = self._try_module_at_path(dirname, name)
        if submodule:
          submodule.name = import_name
          seen.add(import_name)
        if submodule:
          yield submodule
        if recursive and submodule:
          yield from self.iter_package_modules(submodule)


class ModuleGraph(object):
  """
  Represents a network of #ModuleInfo objects.

  # Arguments/Members

  finder (ModuleFinder)

  import_filter (ModuleImportFilter)

  hook (Hook)

  sparse (bool)

    Indicates whether dependencies are collected sparsely. Enabling this
    option is recommended. You can specify packages that are to be collected
    as a whole in the #collect_whole set.

  collect_whole (set)

    A set of packages that are to be collected as a whole, overriding the
    #sparse option. Alternatively, whole collection can be indicated by
    adding a `+` to the module name passed to #collect_modules().
  """

  def __init__(self, finder, import_filter=None, hook=None, sparse=True,
               collect_whole=None, logger=None):
    self.finder = finder
    self.import_filter = import_filter or ModuleImportFilter([])
    self.hook = hook
    self.sparse = sparse
    self.logger = logger or logging.getLogger(__name__)
    self.collect_whole = set(collect_whole or ())
    self._modules = {}

  def __getitem__(self, module_name):
    return self._modules.get(module_name, None)

  def __contains__(self, module_name):
    return module_name in self._modules

  def __iter__(self):
    return iter(self._modules.values())

  def __repr__(self):
    counter = {}
    for mod in self:
      counter[mod.type] = counter.get(mod.type, 0) + 1
    info = ' '.join('{} ({})'.format(v, k) for k, v in counter.items())
    return '<ModuleGraph {}>'.format(info)

  def add(self, module):
    if not isinstance(module, ModuleInfo):
      raise TypeError('module must be ModuleInfo', type(module))
    if module.name in self._modules:
      raise ValueError('module {!r} already in graph'.format(module.name))
    self._modules[module.name] = module
    module.graph = self

  def discard(self, module_name):
    """
    Discard a module from the graph. Does not error if the module is not
    in the graph, but returns #False.
    """

    try:
      del self._modules[module_name]
      return True
    except KeyError:
      return False

  def filter(self, prefix=None, type=None, not_type=None):
    for module in self._modules.values():
      if prefix is not None and not module.name.startswith(prefix):
        continue
      if type is not None and module.type != type:
        continue
      if not_type is not None and module.type == not_type:
        continue
      yield module

  def find_module(self, module_name):
    """
    Finds a module or returns it from the cache.
    """

    module = self._modules.get(module_name)
    if module is None:
      module = self.finder.find_module(module_name)
      self.add(module)
    return module

  def collect_modules(self, module_name, source_module='*', callback=None, depth=0):
    """
    Collects the specified *module_name* and all of its imports into the
    module graph. If *sparse* is set to #True, it will not automatically
    collect submodules if *module_name* is a package.
    """

    if module_name.endswith('+'):
      sparse = False
      module_name = module_name[:-1]
    else:
      sparse = self.sparse and module_name not in self.collect_whole

    module = self.find_module(module_name)
    if source_module is not None:
      module.imported_from.add(source_module)
    if module.sparse in (None, True):
      module.sparse = sparse

    if not module.sparse:
      for sub_module in self.finder.iter_package_modules(module):
        self.collect_modules(sub_module.name, None, callback, depth+1)

    if module.handled:
      return
    module.handled = True

    if self.hook:
      self.hook.inspect_module(module)
    if callback:
      callback(module, depth)

    if module.imports is None:
      module.load_imports()

    for import_name in module.imports:
      if not self.import_filter.accept(import_name, module.name):
        continue
      while import_name:
        # TODO: If self.sparse==False, we should at some point of this
        #       iteration prevent the collection of submodules if they
        #       belong to a completely different subpackage of a namespace
        #       module.
        self.collect_modules(import_name, module.name, callback, depth+1)
        mod = self._modules[import_name]
        if mod.type == mod.NOTFOUND:
          import_name = import_name.rpartition('.')[0]
        else:
          break

  def collect_data(self):
    """
    Invokes the #Hook.collect_data() method for every module in the graph.
    """

    collected = set()
    while True:
      n = 0
      for mod in list(self._modules.values()):
        if mod.type != mod.NOTFOUND and mod.name not in collected:
          n += 1
          collected.add(mod.name)
          self.hook.collect_data(mod)
      if n == 0:
        break


class ModuleImportFilter(object):
  """
  Used in the #ModuleGraph to filter module imports.
  """

  def __init__(self, excludes):
    self.excludes = excludes

  def accept(self, module_name, imported_from):
    """
    Checks if the specified *module_name* is supposed to be excluded from
    the list of *excludes*. An exclude is a string that is either a module
    name or two module names combined by the string `->` like `X->Y` to
    indicate that the module `Y` should be ignored when it is imported from `X`.
    """

    prefix = imported_from + '->' + module_name
    for exclude in self.excludes:
      if imported_from and (prefix == exclude or prefix.startswith(exclude + '.')):
        return False
      if exclude == module_name or module_name.startswith(exclude + '.'):
        return False
    return True


def get_core_modules():
  """
  Returns a list of module names that are core to the Python interpreter.
  """

  libs = ['abc', 'codecs', 'encodings+', 'os', 'site']
  # Note: runpy is only required on Windows for binaries created by
  #       distlib.scripts.ScriptMaker.
  if system.is_purewin:
    libs.append('runpy')
  return libs


def get_common_excludes():
  """
  Returns a list of exclude specifiers for the current platofrm that can be
  passed to the #ModuleImportFilter constructor
  """

  excludes = [
    '_sitebuiltins->pydoc',
    'ctypes->test',
    'heapq->doctest',
    'difflib->doctest',
    'pickle->doctest',
    'keyword->re',
    'token->re',
    'tokenize->argparse',
    'pickle->argparse',
  ]

  if system.is_win:
    excludes.append('_bootlocale->locale')
    excludes.append('sysconfig->_osx_support')
    if not system.is_unix:
      excludes.append('os->posixpath')
  else:
    excludes.append('encodings->_bootlocale')
    excludes.append('os->ntpath')

  if '_thread' in sys.builtin_module_names:
    excludes.append('reprlib->_dummy_thread')

  return excludes
