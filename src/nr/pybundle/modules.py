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

import ast
import copy
import collections
import itertools
import nr.fs
import os
import sys
import sysconfig
import types
from nr.stream import stream
from nr.types import Named

if os.name == 'nt':
  try:
    import pip._internal.pep425tags as tags
  except ImportError:
    import pip.pep425tags as tags
  NATIVE_SUFFIXES = ['.pyd', '.' + tags.implementation_tag + '-' + tags.get_platform() + '.pyd']
  del tags
else:
  NATIVE_SUFFIXES = [sysconfig.get_config_var('SO')]


class ImportInfo(Named):
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

  @property
  def isabs(self):
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
      if parent_module.issubmodule:
        parent_module = parent_module.parent_name
      else:
        parent_module = parent_module.name

    if not isinstance(parent_module, str):
      raise TypeError('parent_module: expected str or ModuleInfo, got {}'
        .format(type(parent_module).__name__))

    if self.isabs:
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
      module_name = prefix + '.' + self.name[level:]

    return ImportInfo(module_name, self.filename, self.lineno, self.is_from_import)


class ModuleInfo(Named):
  __annotations__ = [
    ('name', str),
    ('filename', str),
    ('type', type),
    ('imported_from', list, Named.Initializer(list)),
    ('zippable', bool, None),  #: If the module and its package data can be zipped. Can be resolved to the root module of a package with #check_zippable().
    ('package_data', list, Named.Initializer(list)),  #: A list of paths relative to the package directory that need to be included with the module.
    ('do_default_search', bool, True),  #: ModuleFinder.iter_modules() will check the imports
    ('do_hooks', bool, True), #: ModuleFinder.iter_modules() will check hooks
    ('do_native_deps', bool, True),  #: Do look for native dependencies of this module (only for C extensions)
    ('native_deps_exclude', list, Named.Initializer(list)),  #: A list of native dependencies that should be excluded (absolute paths)
    ('native_deps_path', list, Named.Initializer(list)),  #: A list of paths to resolve native dependencies in, in priority to the standard PATH
    ('children', list, Named.Initializer(list)),  #: A list of child modules
    ('parent', 'ModuleInfo', None),  #: The parent #ModuleInfo
    ('natural', bool, True),  #: Boolean to indicate if the module was found naturally by following the dependency graph
  ]

  SRC = 'src'
  NATIVE = 'native'
  BUILTIN = 'builtin'
  NOTFOUND = 'notfound'

  @property
  def ispkg(self):
    if self.type == self.SRC:
      return os.path.basename(self.filename) == '__init__.py'
    return False

  @property
  def isroot(self):
    return self.name.count('.') == 0

  @property
  def issubmodule(self):
    return not (self.isroot or self.ispkg)

  @property
  def parent_name(self):
    if self.name.count('.') == 0:
      return None
    return self.name.rpartition('.')[0]

  @property
  def relative_filename(self):
    if not self.filename:
      return None
    parts = self.name.split('.')
    parent = os.path.join(*parts[:-1]) if len(parts) > 1 else ''
    if self.type == self.SRC:
      if self.ispkg:
        return os.path.join(parent, parts[-1], '__init__.py')
      else:
        return os.path.join(parent, parts[-1] + '.py')
    else:
      return os.path.join(parent, os.path.basename(self.filename))

  @property
  def relative_directory(self):
    fn = self.relative_filename
    if fn is not None:
      fn = os.path.dirname(fn)
    return fn

  @property
  def directory(self):
    if self.filename is not None:
      return os.path.dirname(self.filename)
    return None

  def check_zippable(self, modules):
    """
    Returns True if the module is zippable. If note defined in this
    #ModuleInfo object, its parent module will be checked which must
    me in the *modules* dictionary. If it is not defined on a root module,
    it will fall back to True.
    """

    while self:
      if self.zippable is not None:
        return self.zippable

      parent = self.parent_name
      if parent is None or parent not in modules:
        return True

      self = modules[parent]


def _find_nodes(ast_node, predicate):
  result = []
  class Visitor(ast.NodeVisitor):
    def visit(self, node):
      if predicate(node):
        result.append(node)
      self.generic_visit(node)
  Visitor().generic_visit(ast_node)
  return result


def get_imports(filename, source=None):
  """
  Returns a list of #ImportInfo tuples for all module imports in the specified
  Python source file or the *source* string. Note that `from X import Y`
  imports could also refer to a member of the module X named Y and not the
  module X.Y.
  """

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
      import_name = parent_name
      if alias.name != '*':
        if not import_name.endswith('.'):
          import_name += '.'
        import_name += alias.name
      result.append(ImportInfo(import_name, filename, node.lineno, True))

  result.sort(key=lambda x: x.lineno)
  return result


def check_module_exclude(module_name, imported_from, excludes):
  for exclude in excludes:
    if imported_from and exclude == (imported_from + '->' + module_name):
      return True
    if exclude == module_name or module_name.startswith(exclude + '.'):
      return True
  return False


class ModuleFinder(object):

  def __init__(self, path=None, excludes=None, native_suffixes=None, hooks=None):
    self.path = path or sys.path
    self.excludes = excludes or []
    self.modules = {}
    if native_suffixes is None:
      native_suffixes = list(NATIVE_SUFFIXES)
    self.native_suffixes = native_suffixes
    self.hooks = hooks or HookFinder()

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

  def examine_module(self, module):
    data = HookData()
    if not module.do_hooks:
      return data
    module.do_hooks = False
    self.hooks.examine(self, module, data)
    return data

  def find_module(self, module_name, imported_from=None, mark_natural=True):
    """
    Attempts to find the module specified by *module_name* in the
    ModuleFinder's search path and returns a #ModuleInfo object.

    For builtin modules, the #ModuleInfo.filename will be None. Note that
    the #ModuleInfo.imported_from is not filled by this method. It is used
    with #ModuleFinder.iter_modules().
    """

    if not module_name:
      raise ValueError('empty module name')
    if module_name in self.modules:
      module = self.modules[module_name]
      if mark_natural:
        module.natural = True
      return module

    if '.' in module_name:
      parent = self.find_module(module_name.rpartition('.')[0], imported_from, mark_natural)
    else:
      parent = None

    if module_name in sys.builtin_module_names:
      module = ModuleInfo(module_name, None, 'builtin', [])
    else:
      parts = module_name.split('.')
      module = None
      for dirname in self.path:
        module = self._try_module_at_path(dirname, module_name)
        if module:
          break
      else:
        module = ModuleInfo(module_name, None, ModuleInfo.NOTFOUND)

    if imported_from is not None:
      module.imported_from = list(imported_from)

    module.parent = parent
    module.natural = mark_natural
    if parent:
      parent.children.append(module)
    self.modules[module_name] = module
    return module

  def find_modules(self, modules, sparse=False):
    """
    Attempts to find all modules in the list of module names *modules*.
    If *sparse* is #False, all package members are gathered even if some of
    the package members haven't been imported.

    The module names in *modules* may be suffixed with a + or - sign
    to indicate that for the specific package the *sparse* flag
    should be explicitly turned on or off.
    """

    def parse_package_spec(spec, collect_whole, collect_sparse):
      if spec[-1] in '+-':
        spec, mode = spec[:-1], spec[-1]
        {'+': collect_whole, '-': collect_sparse}[mode].add(spec)
      return spec

    collect_whole = set()
    collect_sparse = set()
    modules = list(modules)
    for i, module in enumerate(modules):
      modules[i] = parse_package_spec(module, collect_whole, collect_sparse)

    seen = set()
    it = stream.chain(*[self.iter_modules(x, recursive=True) for x in modules])
    for mod in it:
      if mod.type == mod.BUILTIN: continue
      if mod.name in seen: continue
      seen.add(mod.name)

      if not sparse or (mod.name in collect_whole and not mod.name in collect_sparse):
        for submod in self.iter_package_modules(mod):
          if submod.name in seen: continue
          seen.add(submod.name)
          stream.consume(self.iter_modules(submod))

  def iter_modules(self, module=None, filename=None, source=None,
                   excludes=None, recursive=False, include_first=True):
    """
    Iterate over the modules imported by either the specified *module*, the
    Python source file at *filename* or the Python source code that can be
    specified with *source*.

    The *excludes* can be a list of ignored modules or imports that will
    be used in place of the #ModuleInfo.excludes list if specified.

    If *include_first* is set to #True, the first module of which the
    imports are checked will be yielded first, otherwise it will be
    excluded from the iterator.
    """

    if excludes is None:
      excludes = self.excludes

    if not module and not filename and not source:
      raise ValueError('at least one of the parameters "module", "filename" '
                       'or "source" are required')

    if source:
      filename = '<string>'
    if filename:
      if module:
        raise ValueError('parameters "module" and "filename" can not be '
                         'specified at same time')
      module = ModuleInfo('__main__', filename, ModuleInfo.SRC)

    if isinstance(module, str):
      module = self.find_module(module)

    if module.name not in self.modules:
      self.modules[module.name] = module
    elif self.modules[module.name] is not module:
      raise RuntimeError('<module> {!r} already found but this is a '
                         'different ModuleInfo instance'.format(module.name))

    if recursive:
      seen = set()
      def recursion(module):
        if module.name in seen: return
        seen.add(module.name)
        yield module
        for mod in self.iter_modules(module, excludes=excludes,
                                     recursive=False,
                                     include_first=False):
          yield from recursion(mod)
      yield from recursion(module)
      return

    if include_first:
      yield module

    imported_from = [module.name] + module.imported_from

    if module.do_hooks:
      data = self.examine_module(module)
      for import_name in data.imports:
        other_module = self.find_module(import_name, imported_from, module.natural)
        yield other_module
      for module in data.modules:
        yield module

    if module.type == ModuleInfo.SRC and module.do_default_search:
      for imp in get_imports(module.filename, source):
        imp = imp.to_abs(module)
        if check_module_exclude(imp.name, module.name, excludes):
          continue

        other_module = self.find_module(imp.name, imported_from, module.natural)
        if other_module.type == ModuleInfo.NOTFOUND and imp.is_from_import:
          # From imports have the potential to be just member imports, so
          # if we couldn't find a module in a from-import, we check its
          # parent instead.
          parent_imp = imp.parent
          parent_module = self.find_module(parent_imp.name, imported_from, module.natural) if parent_imp else None
          if parent_module and parent_module.type != ModuleInfo.NOTFOUND:
            other_module = parent_module

        # Yield the highest parent module that hasn't been found instead.
        while other_module.type == ModuleInfo.NOTFOUND and other_module.issubmodule:
          other_module = self.find_module(other_module.parent_name, imported_from, module.natural)

        yield other_module

  def iter_package_modules(self, module, recursive=True):
    """
    Iterates over the submodules of the specified *module*. The modules
    found this way are added to the #modules dictionary but are marked as
    being found unnaturally.

    Using this method will not invoke hooks for the submodules.
    """

    if not module.filename or os.path.basename(module.filename) != '__init__.py':
      return; yield  # not a package
    dirname = os.path.dirname(module.filename)
    for name in os.listdir(dirname):
      name = os.path.splitext(name)[0]
      if name == '__init__':
        continue
      import_name = module.name + '.' + name
      if import_name in self.modules:
        submodule = self.modules[import_name]
      else:
        submodule = self._try_module_at_path(dirname, name)
        if submodule:
          submodule.parent = module
          submodule.natural = False
          self.modules[import_name] = submodule
          submodule.name = import_name
      if submodule:
        yield submodule
      if recursive and submodule:
        yield from self.iter_package_modules(submodule)

  def finalize(self):
    while True:
      count = 0
      for mod in list(self.modules.values()):
        if mod.do_hooks:
          self.examine_module(mod)
          count += 1
      if not count:
        break
    self.hooks.finalize(self)


class HookFinder(object):
  """
  This class finds a hook for a module when examining its imports and
  dependencies. A hook is a file called `hook-module.py` where `module` is
  the name of the module that is being hooked. It must provide a `examine()`
  method that accepts a #HookData as its first argument and return a
  #HookResult object.
  """

  def __init__(self, search_path=None):
    if search_path is None:
      search_path = [os.path.join(os.path.dirname(__file__), 'hooks')]
    self.search_path = search_path
    self.cache = {}
    self.catch_all_hooks = None

  def finalize(self, finder):
    self._combine_hooks('finalize', *self.cache.values(), *self.catch_all_hooks)(finder)

  def examine(self, finder, module, result):
    hook = None
    parts = module.name.split('.')
    for i in range(len(parts), 0, -1):
      module_name = '.'.join(parts[:i])
      hook = self._load_hook(module.name)
      if hook is not None:
        break

    if self.catch_all_hooks is None:
      self.catch_all_hooks = []
      for dirname in self.search_path:
        filename = os.path.join(dirname, 'hook.py')
        if os.path.isfile(filename):
          self.catch_all_hooks.append(self._load_module(filename))

    self._combine_hooks('examine', hook, *self.catch_all_hooks)(finder, module, result)

  def _combine_hooks(self, member, *hooks):
    def delegate(*args):
      for hook in hooks:
        if hook is not None and hasattr(hook, member):
          getattr(hook, member)(*args)
    delegate.__name__ = member
    return delegate

  def _load_hook(self, module_name):
    try:
      hook = self.cache[module_name]
    except KeyError:
      for dirname in self.search_path:
        filename = os.path.join(dirname, 'hook-{}.py'.format(module_name))
        if nr.fs.isfile_cs(filename):
          hook = self._load_module(filename)
          break
      else:
        hook = None
      self.cache[module_name] = hook
    return hook

  def _load_module(self, filename):
    with open(filename) as fp:
      name = os.path.basename(filename).rstrip('.py')
      module = types.ModuleType(name)
      module.__file__ = filename
      exec(compile(fp.read(), filename, 'exec'), vars(module))
      return module


class HookData(Named):
  __annotations__ = [
    ('imports', 'Iterable[str]', Named.Initializer(list)), #: A list of absolute module names
    ('modules', 'Iterable[ModuleInfo]', Named.Initializer(list))  #: A list of already resolved ModuleInfo objects
  ]


# A list of core modules that should be included when creating a standalone
# distribution of the CPython interpreter.
# TODO: Are those the same for all CPython versions? Recorded in CPython 3.6
core_libs = ['abc', 'codecs', 'encodings+', 'os', 'site', 'runpy']

# A list of exclude specifiers for imports that commonly make sense to be
# ignored when searching for modules to collect into a standalone distribution
# of the CPython interpreter.
common_excludes = [
  '_sitebuiltins->pydoc',
  'heapq->doctest',
  'pickle->doctest',
  'keyword->re',
  'token->re',
  'tokenize->argparse',
  'pickle->argparse',
]

if sys.platform.startswith('win'):
  common_excludes.append('_bootlocale->locale')
  common_excludes.append('os->posixpath')
else:
  common_excludes.append('encodings->_bootlocale')
  common_excludes.append('os->ntpath')
