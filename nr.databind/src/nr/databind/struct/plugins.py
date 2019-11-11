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

import typing

from nr.collections import abc
from nr.interface import implements
from nr.types.utils import classdef
from nr.types.utils.typing import is_generic, get_generic_args

from ..core.adapters import DefaultTypeMapper
from ..core.errors import ExtractTypeError, ExtractValueError, InvalidTypeDefinitionError
from ..core.interfaces import IConverter, IDataType, ITypeDefAdapter
from ..core.json import JsonObjectMapper
from . import CustomCollection, Struct, StructType


@DefaultTypeMapper.register()
@implements(ITypeDefAdapter)
class StructAdapter(object):

  def adapt(self, mapper, py_type_def):
    if isinstance(py_type_def, type) and issubclass(py_type_def, Struct):
      return StructType(py_type_def)
    raise InvalidTypeDefinitionError(py_type_def)


@JsonObjectMapper.register()
@implements(IConverter)
class StructConverter(object):

  def accept(self, datatype):
    return type(datatype) is StructType

  def deserialize(self, mapper, location):
    if not isinstance(location.value, abc.Mapping):
      raise ExtractTypeError(location)

    struct_cls = location.datatype.struct_cls
    fields = struct_cls.__fields__
    strict = getattr(struct_cls.Meta, 'strict', False)

    kwargs = {}
    handled_keys = set(location.datatype.ignore_keys)
    for name, field in fields.items().sortby(lambda x: x[1].get_priority()):
      assert name == field.name, "woops: {}".format((name, field))
      field.extract_kwargs(mapper, struct_cls, location, kwargs, handled_keys)

    if strict:
      remaining_keys = set(location.value.keys()) - handled_keys
      if remaining_keys:
        raise ExtractValueError(location, "strict object type \"{}\" does not "
          "allow additional keys on extract, but found {!r}".format(
            struct_cls.__name__, remaining_keys))

    obj = object.__new__(struct_cls)

    if mapper.get_option('track_location', False):
      obj.__location__ = location

    try:
      obj.__init__(**kwargs)
    except TypeError as exc:
      raise ExtractTypeError(location)
    return obj

  def serialize(self, mapper, location):
    struct_cls = location.datatype.struct_cls
    if not isinstance(location.value, struct_cls):
      raise ExtractTypeError(location)
    result = {}
    for name, field in struct_cls.__fields__.items():
      if field.is_derived():
        continue
      value = getattr(location.value, name)
      sub_location = location.sub(name, value, field.datatype)
      result[field.name] = mapper.serialize(sub_location)
    return result


@DefaultTypeMapper.register()
@implements(ITypeDefAdapter)
class InlineStructAdapter(object):
  """
  Implements the translation of inline object definitons in dictionary form.
  Example:
  ```py
  datatype = translate_field_type({
    'a': Field(int),
    'b': Field(str),
  })
  assert type(datatype) == ObjectType
  assert sorted(datatype.object_cls.__fields__.keys()) == ['a', 'b']
  ```
  """

  def adapt(self, mapper, py_type_def):
    if isinstance(py_type_def, dict):
      return StructType(type(StructType._INLINE_GENERATED_TYPENAME, (Struct,), py_type_def))
    raise InvalidTypeDefinitionError(py_type_def)


@DefaultTypeMapper.register()
@implements(ITypeDefAdapter)
class CustomCollectionAdapter(object):

  def adapt(self, mapper, py_type_def):
    if isinstance(py_type_def, type) and issubclass(py_type_def, CustomCollection):
      return py_type_def.datatype
    raise InvalidTypeDefinitionError(py_type_def)
