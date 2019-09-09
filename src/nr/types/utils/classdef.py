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

"""
Utils for class definition.
"""

import sys


def hashable_on(key_properties, _stackdepth=0, decorate=None):
  """
  Creates a `__hash__()`, `__eq__()` and `__ne__()` method in the callers
  frame. The functions will hash/compare based on the specified
  *key_properties* (a whitespace/comma separate string or a list of attribute
  names).

  Optionally, the callers stackframe depth can be passed with the
  *_stackdepth* keyword-only argument. The keyword-only argument *decorate*
  may be used to decorate the generated functions.
  """

  if decorate is None:
    def decorate(x):
      return x

  if isinstance(key_properties, str):
    if ',' in key_properties:
      key_properties = [x.strip() for x in key_properties.split(',')]
    else:
      key_properties = key_properties.split()

  @decorate
  def __hash__(self):
    return hash(tuple(getattr(self, k) for k in key_properties))

  @decorate
  def __eq__(self, other):
    if type(self) != type(other):
      return False
    for k in key_properties:
      if getattr(self, k) != getattr(other, k):
        return False
    return True

  @decorate
  def __ne__(self, other):
    if type(self) != type(other):
      return True
    for k in key_properties:
      if getattr(self, k) != getattr(other, k):
        return True
    return False

  frame = sys._getframe(_stackdepth + 1)
  frame.f_locals['__hash__'] = __hash__
  frame.f_locals['__eq__'] = __eq__
  frame.f_locals['__ne__'] = __ne__


def def_repr(properties, _stackdepth=0, decorate=None):
  """
  Defines a `__repr__()` function in the callers frame that renders a
  string of the format `ClassName(attr1="value1", ...)`.
  """

  if decorate is None:
    def decorate(x):
      return x

  @decorate
  def __repr__(self):
    attrs = ', '.join('{}={!r}'.format(k, getattr(self, k)) for k in properties)
    return '{}({})'.format(type(self).__name__, attrs)

  frame = sys._getframe(_stackdepth + 1)
  frame.f_locals['__repr__'] = __repr__
