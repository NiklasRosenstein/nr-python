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
Utils for writing functions. Strongly relies on [[sys._getframe()]].
"""

import sys


def get_caller_name(_stackdepth=0):
  """
  Gets the name of the calling function.
  """

  return sys._getframe(_stackdepth + 1).f_code.co_name


def raise_kwargs(kwargs, name=None, _stackdepth=0):
  """
  Raises a [[TypeError]] indicating that the caller does not accept the
  specified keyword arguments. If *name* is `None`, it will be derived
  with [[get_caller_name()]].
  """

  if kwargs:
    if name is None:
      name = get_caller_name(_stackdepth + 1)
    key = next(iter(kwargs.keys()))

    raise TypeError('{!r} is an invalid keyword argument for {}()'
                    .format(key, name))
