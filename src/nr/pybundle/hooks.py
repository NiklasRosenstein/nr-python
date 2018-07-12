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

import types
import nr.fs


class Hook(object):
  """
  Base class for a hook.
  """

  def inspect_module(self, bundle, graph, module):
    """
    This method is called to retrieve additional information on the module.
    It is called after the module graph has been established, however the
    method may still add additional functions to the module graph.
    """

    raise NotImplementedError


class DelegateHook(Hook):
  """
  Delegates hook calls to hooks loaded from Python scripts.
  """

  def __init__(self, path=None):
    if path is None:
      path = [nr.fs.join(nr.fs.dir(__file__), 'hooks')]
    self.path = path
    self.cache = {}
    self.catch_all_hooks = None
    self.options = {}

  def inspect_module(self, bundle, graph, module):
    self._ensure_hook(module.name)
    for hook in self.cache.values():
      hook.inspect_module(bundle, graph, module)
    for hook in self.catch_all_hooks:
      hook.inspect_module(bundle, graph, module)

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

    if self.catch_all_hooks is None:
      self.catch_all_hooks = []
      for dirname in self.path:
        filename = nr.fs.join(dirname, 'hook.py')
        if nr.fs.isfile(filename):
          self.catch_all_hooks.append(self._load_module(filename))

  def _load_hook(self, module_name):
    """
    Attempts to load a specific hook for the specified *module_name*.
    """

    try:
      hook = self.cache[module_name]
    except KeyError:
      for dirname in self.path:
        filename = nr.fs.join(dirname, 'hook-{}.py'.format(module_name))
        if nr.fs.isfile_cs(filename):
          hook = self._load_module(filename)
          break
      else:
        hook = None
      self.cache[module_name] = hook
    return hook

  def _load_module(self, filename):
    with open(filename) as fp:
      name = nr.fs.base(filename).rstrip('.py')
      module = types.ModuleType(name)
      module.__file__ = filename
      exec(compile(fp.read(), filename, 'exec'), vars(module))
      return module
