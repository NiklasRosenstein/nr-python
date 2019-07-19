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

from .errors import *
from .locator import *
from .types import *
from .object import *


def extract(value, py_type_def, locator=None, **options):
  datatype = translate_field_type(py_type_def)
  if locator is None:
    locator = Locator.Root(value, datatype, options)
  else:
    locator = locator.emplace(value, datatype, options)
  return locator.extract()


def store(value, py_type_def=None, locator=None, **options):
  if py_type_def is None and isinstance(value, Object):
    py_type_def = type(value)

  datatype = translate_field_type(py_type_def)
  if locator is None:
    locator = Locator.Root(value, datatype, options)
  else:
    locator = locator.emplace(value, datatype, options)

  return locator.store()


__all__ = errors.__all__ + locator.__all__ + types.__all__ + object.__all__
__all__ += ['extract', 'store']
