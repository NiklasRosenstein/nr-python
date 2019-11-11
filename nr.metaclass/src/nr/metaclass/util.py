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


def get_staticmethod_func(cm):
  """
  Returns the function wrapped by the #staticmethod *cm*.
  """

  if hasattr(cm, '__func__'):
    return cm.__func__
  else:
    return cm.__get__(int)


def mro_resolve(name, bases, dict):
  """
  Given a tuple of baseclasses and a dictionary that takes precedence
  over any value in the bases, finds a value with the specified *name*
  and returns it. Raises #KeyError if the value can not be found.
  """

  if name in dict:
    return dict[name]
  for base in bases:
    if hasattr(base, name):
      return getattr(base, name)
    try:
      return mro_resolve(name, base.__bases__, {})
    except KeyError:
      pass
  raise KeyError(name)
