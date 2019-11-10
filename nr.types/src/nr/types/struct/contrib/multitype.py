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

from nr.types.interface import implements
from nr.types.utils import classdef

from ..core.adapters import DefaultTypeMapper
from ..core.errors import ExtractTypeError, InvalidTypeDefinitionError
from ..core.interfaces import IDataType, IConverter, ITypeDefAdapter
from ..core.json import JsonObjectMapper


@implements(IDataType)
class MultiType(object):
  """ Represents a collection of datatypes. Uses the first type of the list
  of types that successfully serializes/deserializes. Multi types can be
  defined conveniently using tuples. """

  classdef.comparable(['types'])

  def __init__(self, types):
    self.types = types

  def check_value(self, py_value):
    errors = []
    for datatype in self.types:
      try:
        return datatype.check_value(py_value)
      except TypeError as exc:
        errors.append(exc)
    raise TypeError(errors)


@DefaultTypeMapper.register()
@implements(ITypeDefAdapter)
class MultiTypeAdapter(object):

  def adapt(self, mapper, py_type_def):
    if isinstance(py_type_def, tuple):
      return MultiType([mapper.adapt(x) for x in py_type_def])
    raise InvalidTypeDefinitionError(py_type_def)


@JsonObjectMapper.register()
@implements(IConverter)
class MultiTypeConverter(object):

  def accept(self, datatype):
    return type(datatype) == MultiType

  def _do(self, mapper, location, method):
    errors = []
    for datatype in location.datatype.types:
      try:
        return getattr(mapper, method)(location.replace(datatype=datatype))
      except ExtractTypeError as exc:
        errors.append(exc)
    error_lines = ['Unable to {} "{}"'.format(method, type(location.value).__name__)]
    for error in errors:
      error_lines.append('* {}: {}'.format(
        type(error.location.datatype).__name__, error.message))
    raise ExtractTypeError(location, '\n'.join(error_lines))

  def deserialize(self, mapper, location):
    return self._do(mapper, location, 'deserialize')

  def serialize(self, mapper, location):
    return self._do(mapper, location, 'serialize')



__all__ = ['MultiType']
