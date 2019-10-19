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

from nr.types import abc
from nr.types.interface import implements
from nr.types.utils import classdef
from nr.types.utils.typing import is_generic, get_generic_args

from ..core.adapters import DefaultTypeMapper
from ..core.errors import ExtractTypeError, ExtractValueError, InvalidTypeDefinitionError
from ..core.interfaces import IConverter, IDataType, ITypeDefAdapter
from ..core.json import JsonObjectMapper
from . import CustomCollection, Struct


@implements(IDataType)
class StructType(object):
  """ Represents the datatype for a [[Struct]] subclass. """

  classdef.comparable(['struct_cls', 'ignore_keys'])

  def __init__(self, struct_cls, ignore_keys=None):
    assert isinstance(struct_cls, type), struct_cls
    assert issubclass(struct_cls, Struct), struct_cls
    self.struct_cls = struct_cls
    self.ignore_keys = ignore_keys or []

  def propagate_field_name(self, name):
    if self.struct_cls.__name__ == InlineStructAdapter.GENERATED_TYPE_NAME:
      self.struct_cls.__name__ = name

  def check_value(self, py_value):
    if not isinstance(py_value, self.struct_cls):
      raise TypeError('expected {} instance, got {}'.format(
        self.struct_cls.__name__, type(py_value).__name__))


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

  GENERATED_TYPE_NAME = '_InlineStructAdapter__generated'

  def adapt(self, mapper, py_type_def):
    if isinstance(py_type_def, dict):
      return StructType(type(self.GENERATED_TYPE_NAME, (Struct,), py_type_def))
    raise InvalidTypeDefinitionError(py_type_def)


@DefaultTypeMapper.register()
@implements(ITypeDefAdapter)
class CustomCollectionAdapter(object):

  def adapt(self, mapper, py_type_def):
    if isinstance(py_type_def, type) and issubclass(py_type_def, CustomCollection):
      return py_type_def.datatype
    raise InvalidTypeDefinitionError(py_type_def)


@implements(IDataType)
class UnionType(object):
  """ The UnionType represents multiple types. A value represented by this
  datatype can be of any of the types that are encapsulated by the union
  type. UnionType only supports the encapsulation of [[StructType]]s.

  The UnionType can operate in two modes for the serialization and
  deserialization. In either mode, the object from which the UnionType is
  deserialized must contain a "type" key (configurable with the `type_key`
  parameter).

  In the default mode, the fields for the type are read from the same level.

  ```yaml
  type: onePossibleUnionType
  someField: value
  ```

  With the `nested` option enabled, the values are instead read from an object
  nested with the same name as the type.

  ```yaml
  type: onePossibleUnionType
  onePossibleUnionType:
    someField: value
  ```

  The name of types wrapped by the UnionType can be specified in multiple
  ways. The most common way is to specify a mapping as a parameter to the
  UnionType constructor.

  ```py
  UnionType({
    "onePossibleUnionType": StructOne,
    "another": StructTwo
  })
  ```

  Alternatively, a list of [[Struct]] implementations may be passed, in which
  case the name of the type in the union is derived first from the class-level
  `__union_type_name__` attribute or the class name.

  ```py
  UnionType([StructOne, StructTwo])
  ```

  The [[UnionAdapter]] provides support for declaring unions using typing
  annotations. Note that the same rules for deriving the type name apply as
  for the option where a list is passed to the UnionType constructor.

  ```py
  Union[StructOne, StructTwo]
  ```
  """

  classdef.comparable(['types', 'type_key', 'nested'])

  def __init__(self, types, type_key='type', nested=False):
    # typedef: StructDecl = Union[StructType, Type[Struct]]
    # type: (Union[Dict[str, StructDecl], List[StructDecl]], str, bool)
    self.types = {}
    self.type_key = type_key
    self.nested = nested

    def get_struct_cls(item):
      if isinstance(item, StructType):
        return item.struct_cls
      elif isinstance(item, type) and issubclass(item, Struct):
        return item
      else:
        raise TypeError('expected StructType instance or Struct class, '
          'got {}'.format(type(item).__name__))

    if isinstance(types, (list, tuple)):
      for item in types:
        struct_cls = get_struct_cls(item)
        name = getattr(struct_cls, '__union_type_name__', struct_cls.__class__)
        self.types[name] = struct_cls
    elif isinstance(types, abc.Mapping):
      for key, value in types.items():
        self.types[key] = get_struct_cls(value)
    else:
      raise TypeError('expected list/tuple/dict, got {}'
                      .format(type(types).__name__))

  def check_value(self, py_value):
    if not any(isinstance(py_value, x) for x in self.types.values()):
      raise TypeError('expected {{{}}}, got {}'.format(
        '|'.join(sorted(x.__name__ for x in self.types.values())),
        type(py_value).__name__))
    return py_value


@DefaultTypeMapper.register()
@implements(ITypeDefAdapter)
class UnionAdapter(object):

  def adapt(self, mapper, py_type_def):
    if is_generic(py_type_def, typing.Union):
      union_types = get_generic_args(py_type_def)
      return UnionType(union_types)
    raise InvalidTypeDefinitionError(py_type_def)


@JsonObjectMapper.register()
@implements(IConverter)
class UnionConverter(object):

  def accept(self, datatype):
    return type(datatype) == UnionType

  def deserialize(self, mapper, location):
    if not isinstance(location.value, abc.Mapping):
      raise ExtractTypeError(location)

    datatype = location.datatype  # type: UnionType
    type_key = datatype.type_key
    if type_key not in location.value:
      raise ExtractValueError(location,
        'required key "{}" not found'.format(type_key))

    type_name = location.value[type_key]
    if type_name not in datatype.types:
      raise ExtractValueError(location,
        'unknown union type: "{}"'.format(type_key))

    if datatype.nested:
      struct_type = StructType(datatype.types[type_name])
      location = location.sub(type_key, location.value[type_key], struct_type)
    else:
      struct_type = StructType(datatype.types[type_name], ignore_keys=[type_key])
      location = location.replace(datatype=struct_type)

    return mapper.deserialize(location)

  def serialize(self, mapper, location):
    datatype = location.datatype
    value = location.value
    try:
      type_name, struct_type = next((k, v) for k, v in datatype.types.items()
                                    if v == type(value))
    except StopIteration:
      try:
        datatype.check_value(value)  # reuse error message thrown here
      except TypeError as exc:
        raise ExtractTypeError(location, exc)
      else:
        raise RuntimeError('expected UnionType.check_value() to raise')

    if datatype.nested:
      struct_type = StructType(struct_type)
      location = location.sub(type_key, location.value, struct_type)
    else:
      struct_type = StructType(struct_type, ignore_keys=[datatype.type_key])
      location = location.replace(datatype=struct_type)

    result = {datatype.type_key: type_name}
    result.update(mapper.serialize(location))
    return result
