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
import collections
import itertools
import os
import sys
import sysconfig
import types
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
    ('lineno', int)
  ]


class ModuleInfo(Named):
  __annotations__ = [
    ('name', str),
    ('filename', str),
    ('type', type),
    ('imported_from', list, Named.Initializer(list))
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
  def relative_filename(self):
    if not self.filename:
      return None
    if self.type == self.SRC:
      if self.ispkg:
        return os.path.join(os.path.join(*self.name.split('.')), '__init__.py')
      else:
        return os.path.join(*self.name.split('.')) + '.py'
    else:
      return os.path.basename(self.filename)

  def join_import_from(self, import_spec):
    """
    Joins a relative import like `from .foo import bar` with this module as
    its parent module. If the module is not a root module or package root,
    it will be joined with the package root.
    """

    if not self.isroot and not self.ispkg:
      parent = self.name.rpartition('.')[0]
    else:
      parent = self.name
    return join_import_from(import_spec, parent)


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
      result.append(ImportInfo(alias.name, filename, node.lineno))
  for node in _find_nodes(module, lambda x: isinstance(x, ast.ImportFrom)):
    parent_name = '.' * node.level + (node.module or '')
    result.append(ImportInfo(parent_name, filename, node.lineno))
    for alias in node.names:
      import_name = parent_name
      if alias.name != '*':
        if not import_name.endswith('.'):
          import_name += '.'
        import_name += alias.name
      result.append(ImportInfo(import_name, filename, node.lineno))

  result.sort(key=lambda x: x.lineno)
  return result


def join_import_from(import_spec, parent_module):
  level = sum(1 for _ in itertools.takewhile(lambda x: x == '.', import_spec))
  if level == 0:
    return import_spec
  elif level == 1:
    submodule = import_spec.lstrip('.')
    if submodule:
      return parent_module + '.' + submodule
    else:
      return parent_module
  else:
    prefix = '.'.join(parent_module.split('.')[:-level+1])
    if not prefix:
      raise ValueError('import {!r} from {!r} is invalid'.format(
        import_spec, parent_module))
    return prefix + '.' + import_spec[level:]


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

  def find_module(self, module_name):
    """
    Attempts to find the module specified by *module_name* in the
    ModuleFinder's search path and returns a #ModuleInfo object.

    For builtin modules, the #ModuleInfo.filename will be None. Note that
    the #ModuleInfo.imported_from is not filled by this method. It is used
    with #ModuleFinder.iter_modules().
    """

    if not module_name:
      raise ValueError('empty module name')
    if module_name in sys.builtin_module_names:
      return ModuleInfo(module_name, None, 'builtin', [])
    if module_name in self.modules:
      return self.modules[module_name]

    parts = module_name.split('.')
    result = None
    for dirname in self.path:
      # TODO: Configurable behaviour for Python 2 where __init__.py is
      #       required and namespace packages are not automatically
      #       supported.
      result = self.get_module_info_from_basename(module_name, os.path.join(dirname, *parts))
      if result: break
    else:
      return ModuleInfo(module_name, None, ModuleInfo.NOTFOUND)

    self.modules[module_name] = result
    return result

  def iter_modules(self, module=None, filename=None, source=None, excludes=None):
    """
    An iterator for the modules that are imported by the specified *module*
    or Python source file. The returned #ModuleInfo objects have their
    *imported_from* member filled in order to be able to track how a module
    was imported.
    """

    if excludes is None:
      excludes = self.excludes

    if not filename:
      if not module:
        raise ValueError('need either module or filename parameter')
      if not isinstance(module, ModuleInfo):
        module = self.find_module(module)
      if not module.filename or module.type == 'native':
        return
    else:
      module = ModuleInfo('__main__', filename, ModuleInfo.SRC)

    seen = set()
    stack = collections.deque()

    for imp in get_imports(module.filename, source):
      stack.appendleft((module.join_import_from(imp.name), [module.name]))

    while stack:
      import_name, imported_from = stack.pop()
      if import_name in seen:
        continue
      seen.add(import_name)
      if check_module_exclude(import_name, imported_from[0] if imported_from else None, excludes):
        continue

      module = self.find_module(import_name)
      module.imported_from[:] = imported_from
      yield module

      hook = self.hooks.find_hook(module.name)
      if hook:
        result = hook(HookData(self, module))
        yield from result.modules

      if module.type == ModuleInfo.SRC:
        imported_from = [module.name] + imported_from
        for imp in get_imports(module.filename):
          stack.append((module.join_import_from(imp.name), imported_from))

  def iter_package_modules(self, module, recursive=True):
    if os.path.basename(module.filename) != '__init__.py':
      return; yield  # not a package
    dirname = os.path.dirname(module.filename)
    for name in os.listdir(dirname):
      if name.endswith('.py'):
        name = name[:-3]
      if name == '__init__':
        continue
      path = os.path.join(dirname, name)
      submodule = self.get_module_info_from_basename(module.name + '.' + name, path)
      if submodule:
        yield submodule
        if recursive:
          yield from self.iter_package_modules(submodule)

  def get_module_type(self, filename):
    if not os.path.isfile(filename):
      return None
    if filename.endswith('.py'):
      return ModuleInfo.SRC
    for suffix in self.native_suffixes:
      if filename.endswith(suffix):
        return ModuleInfo.NATIVE
    return None

  def get_module_info_from_basename(self, module_name, basename):
    kind = self.get_module_type(basename + '.py')
    if kind is not None:
      return ModuleInfo(module_name, basename + '.py', kind)
    kind = self.get_module_type(os.path.join(basename, '__init__.py'))
    if kind:
      return ModuleInfo(module_name, os.path.join(basename, '__init__.py'), kind)
    for suffix in self.native_suffixes:
      kind = self.get_module_type(basename + suffix)
      if kind:
        return ModuleInfo(module_name, basename + suffix, kind)
    return None


class HookFinder(object):
  """
  This class finds a hook for a module when examining its imports and
  dependencies. A hook is a file called `hook-module.py` where `module` is
  the name of the module that is being hooked. It must provide a `examine()`
  method that accepts a #HookData as its first argument and return a
  #HookResult object.
  """

  package_dir = os.path.join(os.path.dirname(__file__), 'hooks')

  def __init__(self):
    self.cache = {}

  def find_hook(self, module_name):
    parts = module_name.split('.')
    for i in range(len(parts), 0, -1):
      module_name = '.'.join(parts[:i])

      # Load the hook into the cache, or fill the cache with
      # None if the hook does not exist.
      if module_name not in self.cache:
        filename = os.path.join(os.getcwd(), 'hooks', 'hook-{}.py'.format(module_name))
        if not os.path.isfile(filename):
          filename = os.path.join(self.package_dir, 'hook-{}.py'.format(module_name))
        if os.path.isfile(filename):
          module = self._load_module(filename)
          hook = module.examine
        else:
          hook = None
        self.cache[module_name] = hook

      hook = self.cache[module_name]
      if hook is not None:
        return hook
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
    ('finder', ModuleFinder),
    ('module', ModuleInfo)
  ]


class HookResult(Named):
  __annotations__ = [
    ('modules', 'Iterable[ModuleInfo]')
  ]
