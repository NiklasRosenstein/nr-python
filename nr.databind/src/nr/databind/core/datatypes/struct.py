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

from ..interfaces import IDataType
from ..errors import InvalidTypeDefinitionError
from nr.commons.py import classdef
from nr.interface import implements

__all__ = ['StructType']


@implements(IDataType)
class StructType(object):
  """ Represents the datatype for a [[Struct]] subclass. """

  classdef.comparable(['struct_cls', 'ignore_keys'])
  _INLINE_GENERATED_TYPENAME = '_InlineStructAdapter__generated'

  def __init__(self, struct_cls, ignore_keys=None):
    assert isinstance(struct_cls, type), struct_cls
    assert issubclass(struct_cls, Struct), struct_cls
    self.struct_cls = struct_cls
    self.ignore_keys = ignore_keys or []

  def propagate_field_name(self, name):
    if self.struct_cls.__name__ == self._INLINE_GENERATED_TYPENAME:
      self.struct_cls.__name__ = name

  @classmethod
  def from_typedef(cls, recursive, py_type_def):
    # Struct subclass
    if isinstance(py_type_def, type) and issubclass(py_type_def, Struct):
      return cls(py_type_def)
    # Inline definition
    if isinstance(py_type_def, dict):
      return cls(type(cls._INLINE_GENERATED_TYPENAME, (Struct,), py_type_def))
    raise InvalidTypeDefinitionError(py_type_def)

  def check_value(self, py_value):
    if not isinstance(py_value, self.struct_cls):
      raise TypeError('expected {} instance, got {}'.format(
        self.struct_cls.__name__, type(py_value).__name__))


from ..struct import Struct
