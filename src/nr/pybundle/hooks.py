# -*- coding: utf8 -*-
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

"""
Implements the procedure of finding and executing hooks that are used to
provide additional information when Python modules are collected.
"""

import logging
import nr.fs
import types

logger = logging.getLogger(__name__)


class Hook(object):
  """
  Base class for a hook.
  """

  def inspect_module(self, module):
    """
    This method is called to retrieve additional information on the module,
    such as additional imports that it performs.
    """

    pass

  def collect_data(self, module):
    """
    Called when the module was found by a #ModuleFinder before its imports
    are inspected.
    """

    pass


class HookOptions(dict):

  def get_bool(self, key, default=False):
    value = self.get(key, default)
    if isinstance(value, str):
      value = value.strip().lower()
      if value in ('y', 'yes', 'true', '1'):
        value = True
      elif value in ('n', 'no', 'false', '0'):
        value = False
      else:
        logger.warn('Invalid hook option value {!r}: expected bool'
                    .format(value))
        value = False
    return value


class ScriptHook(Hook):

  def __init__(self, module_name, filename, options):
    self.module_name = module_name
    self.filename = filename
    self.options = options
    with open(filename) as fp:
      name = nr.fs.base(filename).rstrip('.py')
      self.module = types.ModuleType(name)
      self.module.__file__ = filename
      self.module.options = options
      exec(compile(fp.read(), filename, 'exec'), vars(self.module))
    if hasattr(self.module, 'inspect_module'):
      self.inspect_module = self.module.inspect_module
    if hasattr(self.module, 'collect_data'):
      self.collect_data = self.module.collect_data

  def __repr__(self):
    return '<ScriptHook filename={!r}>'.format(self.filename)

  def matches(self, module_name):
    if self.module_name is None:
      return module_name is None
    return self.module_name == module_name or \
        module_name.startswith(self.module_name + '.')


class DelegateHook(Hook):
  """
  Delegates hook calls to hooks loaded from Python scripts.
  """

  def __init__(self, path=None, options=None):
    if path is None:
      path = [nr.fs.join(nr.fs.dir(__file__), 'hooks')]
    self.path = path
    self.options = HookOptions(options or {})
    self._module_hooks = {}
    self._general_hooks = None

  def inspect_module(self, module):
    for hook in self._hooks_for(module.name):
      hook.inspect_module(module)

  def collect_data(self, module):
    for hook in self._hooks_for(module.name):
      hook.collect_data(module)

  def _hooks_for(self, module_name):
    self._ensure_hook(module_name)
    yield from [x for x in self._module_hooks.values()
        if x and x.matches(module_name)]
    yield from self._general_hooks

  def _ensure_hook(self, module_name):
    """
    Ensures that the hook for the specified *module_name* is loaded.
    """

    hook = None
    parts = module_name.split('.')
    for i in range(len(parts), 0, -1):
      sub_name = '.'.join(parts[:i])
      hook = self._load_hook(sub_name)
      if hook is not None:
        break

    if self._general_hooks is None:
      self._general_hooks = []
      for dirname in self.path:
        filename = nr.fs.join(dirname, 'hook.py')
        if nr.fs.isfile(filename):
          self._general_hooks.append(ScriptHook(None, filename, self.options))

  def _load_hook(self, module_name):
    """
    Attempts to load a specific hook for the specified *module_name*.
    """

    try:
      hook = self._module_hooks[module_name]
    except KeyError:
      for dirname in self.path:
        filename = nr.fs.join(dirname, 'hook-{}.py'.format(module_name))
        if nr.fs.isfile_cs(filename):
          hook = ScriptHook(module_name, filename, self.options)
          break
      else:
        hook = None
      self._module_hooks[module_name] = hook
    return hook
