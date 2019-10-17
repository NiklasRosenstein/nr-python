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

from ..core.interfaces import Location
from .struct import CustomCollection, Struct
from .fields import *
from .globals import get_type_mapper
from .plugins import StructType


def deserialize(mapper, data, py_type_def, type_mapper=None, _stackdepth=0):
  if type_mapper is None:
    type_mapper = get_type_mapper(None, _stackdepth + 1)
  datatype = type_mapper.adapt(py_type_def)
  return mapper.deserialize(Location(None, None, data, datatype))


def serialize(mapper, data, py_type_def, type_mapper=None, _stackdepth=0):
  if type_mapper is None:
    type_mapper = get_type_mapper(None, _stackdepth + 1)
  datatype = type_mapper.adapt(py_type_def)
  return mapper.deserialize(Location(None, None, data, datatype))


__all__ = [
  'CustomCollection',
  'Struct',
  'deserialize',
  'serialize',
  'StructType'
] + fields.__all__
