# The MIT License (MIT)
#
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


_Import = collections.namedtuple('_Import', 'name filename lineno')
_Module = collections.namedtuple('_Module', 'name filename type imported_from')


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
  Returns a list of #Import tuples for all module imports in the specified
  Python source file or the *source* string.
  """

  if source is None:
    with open(filename, 'rb') as fp:
      source = fp.read()

  module = ast.parse(source, filename)
  result = []

  for node in _find_nodes(module, lambda x: isinstance(x, ast.Import)):
    for alias in node.names:
      result.append(_Import(alias.name, filename, node.lineno))
  for node in _find_nodes(module, lambda x: isinstance(x, ast.ImportFrom)):
    import_name = '.' * node.level + (node.module or '')
    result.append(_Import(import_name, filename, node.lineno))

  result.sort(key=lambda x: x.lineno)
  return result


def join_import_from(import_spec, parent_module):
  level = sum(1 for _ in itertools.takewhile(lambda x: x == '.', import_spec))
  if level == 0:
    return import_spec
  elif level == 1:
    return parent_module
  else:
    prefix = '.'.join(parent_module.split('.')[:-level+1])
    if not prefix:
      raise ValueError('import {!r} from {!r} is invalid'.format(
        import_spec, parent_module))
    return prefix + '.' + import_spec[level:]


class ModuleFinder(object):

  def __init__(self, path=None, excludes=None):
    self.path = path or sys.path
    self.excludes = excludes or []
    self.modules = {}

  def find_module(self, module_name):
    """
    Attempts to find the module specified by *module_name* in the
    ModuleFinder's search path and returns a #_Module tuple. The following
    module types can be returned:

    * `"builtin"`
    * `"native"`
    * `"src"`
    * `"notfound"`

    For the native and notfound types, the module's filename will be #None.
    The *imported_from* member of the returned tuple will be an empty list.
    This list is filled when using #iter_modules().
    """

    if not module_name:
      raise ValueError('empty module name')
    if module_name in sys.builtin_module_names:
      return _Module(module_name, None, 'builtin', [])
    if module_name in self.modules:
      return self.modules[module_name]

    parts = module_name.split('.')
    so = sysconfig.get_config_var('SO')
    for dirname in self.path:
      # TODO: Configurable behaviour for Python 2 where __init__.py is
      #       required and namespace packages are not automatically
      #       supported.
      script_file = os.path.join(dirname, os.sep.join(parts)) + '.py'
      if os.path.isfile(script_file):
        result = _Module(module_name, script_file, 'src', [])
        break
      package_file = os.path.join(dirname, os.sep.join(parts), '__init__.py')
      if os.path.isfile(package_file):
        result = _Module(module_name, package_file, 'src', [])
        break
      native_file = os.path.join(dirname, os.sep.join(parts)) + so
      if os.path.isfile(native_file):
        result = _Module(module_name, native_file, 'native', [])
        break
    else:
      return _Module(module_name, None, 'notfound', [])

    self.modules[module_name] = result
    return result

  def iter_modules(self, module=None, filename=None, source=None):
    """
    An iterator for the modules that are imported by the specified *module*
    or Python source file. The returned #_Module tuples have the
    *imported_from* member filled in order to be able to track how a module
    was imported.
    """

    if not filename:
      if not module:
        raise ValueError('need either module or filename parameter')
      module = self.find_module(module)
      if not module.filename or module.type == 'native':
        return
    else:
      module = _Module('__main__', filename, 'src', [])

    seen = set()
    stack = collections.deque()

    for imp in get_imports(module.filename, source):
      stack.appendleft((join_import_from(imp.name, module.name), [module.name]))

    yield module
    while stack:
      import_name, imported_from = stack.pop()
      if import_name in seen:
        continue
      seen.add(import_name)

      module = self.find_module(import_name)
      module.imported_from[:] = imported_from
      yield module

      if module.type == 'src':
        imported_from = [module.name] + imported_from
        for imp in get_imports(module.filename):
          stack.append((join_import_from(imp.name, module.name), imported_from))
