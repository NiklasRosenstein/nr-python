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
from nr.types.utils.funcdef import raise_kwargs


def hashable_on(key_properties, **kwargs):
  """
  Creates a `__hash__()`, `__eq__()` and `__ne__()` method in the callers
  frame. The functions will hash/compare based on the specified
  *key_properties*.

  Optionally, the callers stackframe depth can be passed with the
  *_stackdepth* keyword-only argument. The keyword-only argument *decorate*
  may be used to decorate the generated functions.
  """

  _stackdepth = kwargs.pop('_stackdepth', None)
  decorate = kwargs.pop('decorate', lambda x: x)
  raise_kwargs(kwargs)

  def __hash__(self):
    return hash(tuple(getattr(self, k) for k in key_properties))

  def __eq__(self, other):
    if type(self) != type(other):
      return False
    for k in key_properties:
      if getattr(self, k) != getattr(other, k):
        return False
    return True

  def __ne__(self, other):
    if type(self) != type(other):
      return True
    for k in key_properties:
      if getattr(self, k) != getattr(other, k):
        return True
    return False

  frame = sys._getframe(1)
  frame.f_locals['__hash__'] = decorate(__hash__)
  frame.f_locals['__eq__'] = decorate(__eq__)
  frame.f_locals['__ne__'] = decorate(__ne__)
