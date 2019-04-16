# -*- coding: utf8 -*-
# Copyright (c) 2019 Niklas Rosenstein
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

import sys
import types


class _InheritableModuleType(type):
  """
  Metaclass for a class type that wraps a module object and allow accessing
  members of that module or subclassing it.
  """

  def __new__(cls, name, bases, attrs):
    if bases == (types.ModuleType,):
      return type.__new__(cls, name, bases, attrs)
    for base in bases:
      if isinstance(base, _InheritableModuleType):
        module = base.__wrap_module__
        inheritable_type = base.__inheritable_type__
        break
    else:
      raise RuntimeError
    bases = tuple(x for x in bases if not isinstance(x, _InheritableModuleType))
    return type(name, (inheritable_type,) + bases, attrs)

  def __getattr__(self, name):
    return getattr(self.__wrap_module__, name)

  def __repr__(self):
    return '<inheritable ' + repr(self.__wrap_module__)[1:]


def create_inheritable_module(module, inheritable_type):
  """
  Wraps the specified *module* object and returns a class that can be
  subclassed to result in a direct subclass of *inheritable_type*.
  """

  return _InheritableModuleType(module.__name__, (types.ModuleType,),
    {'__wrap_module__': module, '__inheritable_type__': inheritable_type})


def make_inheritable(module_name, inheritable_type):
  """
  Makes the module with the specified *module_name* inheritable to the
  specified *inheritable_type*.
  """

  sys.modules[module_name] = create_inheritable_module(
    sys.modules[module_name], inheritable_type)
