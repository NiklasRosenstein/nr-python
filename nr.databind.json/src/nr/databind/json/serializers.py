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

from nr.collections import abc, ChainDict
from nr.databind.core import IDeserializer, ISerializer, Module, SerializerCollection, \
  SerializationTypeError
from nr.databind.core.collection import Collection
from nr.databind.core.datatypes import *
from nr.databind.core.decorations import *
from nr.databind.core.struct import Struct, StructType
from nr.databind.core.union import UnionType, UnknownUnionTypeError
from nr.databind.json.decorations import *
from nr.interface import implements, override
from nr.parsing.date import Iso8601
from nr.pylang.utils import NotSet
from nr.pylang.utils import classdef
import datetime
import decimal
import six


@implements(IDeserializer, ISerializer)
class AnySerializer(object):

  def deserialize(self, mapper, node):
    return node.value

  def serialize(self, mapper, node):
    return node.value


@implements(IDeserializer, ISerializer)
class BooleanSerializer(object):

  def deserialize(self, mapper, node):
    if isinstance(node.value, bool):
      return node.value
    raise node.type_error()

  def serialize(self, mapper, node):
    if node.datatype.strict and not isinstance(node.value, bool):
      raise node.type_error()
    return bool(node.value)


@implements(IDeserializer, ISerializer)
class StringSerializer(object):

  def deserialize(self, mapper, node):
    if isinstance(node.value, six.string_types):
      return node.value
    if node.datatype.strict:
      raise node.type_error()
    return str(node.value)

  serialize = deserialize


@implements(IDeserializer, ISerializer)
class IntegerSerializer(object):

  def deserialize(self, mapper, node):
    try:
      return node.datatype.isinstance_check(node.value, False, True)
    except TypeError as exc:
      raise node.type_error(exc)

  serialize = deserialize


@implements(IDeserializer, ISerializer)
class DecimalSerializer(object):

  def __init__(self, supports_decimal=False, as_string=None):
    super(DecimalSerializer, self).__init__()
    self.supports_decimal = supports_decimal
    self.as_string = as_string

  def deserialize(self, mapper, node):
    if not isinstance(node.value, node.datatype.accepted_input_types):
      raise node.type_error()
    return node.datatype.coerce(node.value)

  def serialize(self, mapper, node):
    if not isinstance(node.value, node.datatype.accepted_input_types):
      raise node.type_error()
    if node.datatype.strict and isinstance(node.value, six.string_types):
      raise node.type_error()

    value = node.datatype.coerce(node.value)
    is_decimal = isinstance(value, decimal.Decimal)

    if self.supports_decimal and self.as_string is None and is_decimal:
      return value
    if self.as_string or (self.as_string is None and is_decimal):
      return str(value)
    return float(value)


@implements(IDeserializer, ISerializer)
class CollectionSerializer(object):
  """
  Serializes the [[CollectionType]] from a Python collection object to a
  list (for serialization in JSON). If the underlying Python type is
  unordered, the values will be sorted by their hash.
  """

  def deserialize(self, mapper, node):
    # Check if the value we receive is actually a collection.
    try:
      node.datatype.isinstance_check(node.value, False, False)
    except TypeError:
      raise node.type_error()

    # Deserialize child elements.
    item_type = node.datatype.item_type
    result = []
    for index, item in enumerate(node.value):
      result.append(mapper.deserialize_node(node.make_child(index, item_type, item)))

    # Convert to the designated Python type.
    py_type = node.datatype.py_type
    if not isinstance(py_type, type) or not isinstance(result, py_type):
      result = py_type(result)

    if node.get_decoration(StoreNode) and hasattr(result, '__databind__'):
      result.__databind__['node'] = node

    return result

  def serialize(self, mapper, node):
    # Check if the value we receive is actually a collection.
    try:
      node.datatype.isinstance_check(node.value, False, False)
    except TypeError:
      raise node.type_error()

    # Serialize child elements.
    item_type = node.datatype.item_type
    result = []
    for index, item in enumerate(node.value):
      result.append(mapper.serialize_node(node.make_child(index, item_type, item)))

    # Convert to the designated JSON type.
    config = node.get_decoration(JsonSerializeCollectionAs)
    if config:
      json_type = config.cls
    else:
      json_type = list

    if not isinstance(json_type, type) or not isinstance(result, json_type):
      result = json_type(result)

    return result


@implements(IDeserializer, ISerializer)
class ObjectSerializer(object):

  def deserialize(self, mapper, node):
    if not isinstance(node.value, abc.Mapping):
      raise node.type_error()
    value_type = node.datatype.value_type
    result = node.datatype.py_type()
    for key in node.value:
      result[key] = mapper.deserialize_node(node.make_child(key, value_type, node.value[key]))
    return result

  def serialize(self, mapper, node):
    if not isinstance(node.value, abc.Mapping):
      raise node.type_error()
    config = node.get_decoration(JsonSerializeObjectAs)
    if config:
      result = config.cls()
    else:
      result = {}
    value_type = node.datatype.value_type
    for key in node.value:
      result[key] = mapper.serialize_node(node.make_child(key, value_type, node.value[key]))
    return result


@implements(IDeserializer, ISerializer)
class StructSerializer(object):

  def _extract_kwargs(self, mapper, field, struct_cls, node, kwargs, handled_keys):
    if field.name in kwargs:
      raise RuntimeError('StructSerializer._extract_kwargs() called for field {!r} which is'
                         'already present in extraction target.'.format(field.name))

    if get_decoration(Raw, field.decorations):
      kwargs[field.name] = node.value
      return

    json_remainder = get_decoration(Remainder, field.decorations)
    if json_remainder:
      if not isinstance(field.datatype, ObjectType):
        raise RuntimeError('"{}.{}" expected ObjectType due to JsonRemainder '
          'decoration, got {}'.format(struct_cls.__name__, field.name,
            type(node.datatype).__name__))
      result = {}
      for key in node.value:
        if key not in handled_keys:
          result[key] = mapper.deserialize_node(node.make_child(
            key, field.datatype.value_type, node.value[key], decorations=field.decorations))
          handled_keys.add(key)
      kwargs[field.name] = result
      return

    # Retrieve decorations that will affect the deserialization of this field.
    json_default = get_decoration(JsonDefault, field.decorations)
    json_field_name = get_decoration(JsonFieldName, field.decorations) or \
      get_decoration(FieldName, field.decorations)
    json_field_validator = get_decoration(Validator, field.decorations)

    key = json_field_name.name if json_field_name else field.name
    if key not in node.value:
      json_object_key = get_decoration(InheritKey, field.decorations)
      if json_object_key:
        kwargs[field.name] = node.key
        return
      if field.required or (field.default is NotSet and not json_default):
        msg = 'member "{}" is missing for {} object'.format(key, struct_cls.__name__)
        raise node.value_error(msg)
      if json_default:
        value = json_default.value
      else:
        return
    else:
      value = node.value[key]

    if field.nullable and value is None:
      kwargs[field.name] = None
    else:
      kwargs[field.name] = mapper.deserialize_node(node.make_child(
        key, field.datatype, value, decorations=field.decorations))

    if json_field_validator:
      kwargs[field.name] = json_field_validator(kwargs[field.name])

    handled_keys.add(key)

  def deserialize(self, mapper, node):
    # Check if there is a custom deserializer on the struct class.
    struct_cls = node.datatype.struct_cls
    config = JsonSerializer.get(struct_cls)

    obj = None
    if config:
      deserializer = config.get_deserializer(struct_cls)
      if deserializer:
        try:
          obj = deserializer.deserialize(mapper, node)
        except NotImplementedError:
          pass

    if obj is None:
      obj = self._deserialize(mapper, node)

    validator = node.get_decoration(Validator)  # TODO: Only consider node-level and class decorations
    if validator:
      try:
        validator(obj)
      except ValueError as exc:
        raise node.value_error(exc)
      except TypeError as exc:
        raise node.type_error(exc)

    return obj

  def _deserialize(self, mapper, node):
    struct_cls = node.datatype.struct_cls

    # Otherwise, we expect a mapping.
    if not isinstance(node.value, abc.Mapping):
      raise node.type_error()

    fields = struct_cls.__fields__
    strict = node.get_decoration(Strict)

    kwargs = {}
    handled_keys = set(node.datatype.ignore_keys)
    remainder_fields = []
    for name, field in fields.items().sortby(lambda x: x[1].get_priority()):
      if field.hidden:
        continue
      if get_decoration(Remainder, field.decorations):
        remainder_fields.append(field)
        continue
      assert name == field.name, "woops: {}".format((name, field))
      self._extract_kwargs(mapper, field, struct_cls, node, kwargs, handled_keys)

    for field in remainder_fields:
      self._extract_kwargs(mapper, field, struct_cls, node, kwargs, handled_keys)

    remaining_keys = set(node.value.keys()) - handled_keys
    if remaining_keys and strict:
      raise node.value_error(
        'strict object type "{}" does not allow additional keys on extract, but found {!r}'
        .format(struct_cls.__name__, remaining_keys))
    node.unknowns.update(remaining_keys)

    obj = object.__new__(struct_cls)

    try:
      obj.__init__(**kwargs)
    except TypeError as exc:
      raise node.type_error(exc)

    if node.get_decoration(StoreNode):
      obj.__databind__['node'] = node

    return obj

  def serialize(self, mapper, node):
    struct_cls = node.datatype.struct_cls
    if not isinstance(node.value, struct_cls):
      raise node.type_error()

    # Check if there is a custom serializer on the struct class.
    result = NotSet
    config = JsonSerializer.get(struct_cls)
    if config:
      serializer = config.get_serializer(struct_cls)
      if serializer:
        try:
          result = serializer.serialize(mapper, node)
        except NotImplementedError:
          pass

    if result is NotSet:
      skip_default_values = node.get_decoration(SkipDefaults)
      serialize_as = node.get_local_decoration(SerializeAs)
      result = serialize_as.cls() if serialize_as else {}
      for name, field in struct_cls.__fields__.items():
        if field.hidden or get_decoration(Raw, field.decorations):
          continue

        value = getattr(node.value, name)
        if not (field.nullable and value is None):
          value = mapper.serialize_node(node.make_child(
            name, field.datatype, value, decorations=field.decorations))

        if field.default is not NotSet and skip_default_values and \
            value == field.get_default_value():
          continue

        json_object_key = get_decoration(InheritKey, field.decorations)
        if json_object_key and node.key == value:
          continue

        json_field_name = get_decoration(JsonFieldName, field.decorations) or \
          get_decoration(FieldName, field.decorations)
        key = json_field_name.name if json_field_name else field.name

        json_remainder = get_decoration(Remainder, field.decorations)
        if json_remainder:
          result.update(value)
        else:
          result[key] = value

    return result


@implements(IDeserializer, ISerializer)
class DatetimeSerializer(object):

  DEFAULT_FORMAT = Format(Iso8601)
  _TYPE = datetime.datetime

  def __init__(self, serialize_as_string=True):
    self.serialize_as_string = serialize_as_string

  @classmethod
  def _get_format(cls, node):  # type: (Node) -> Format
    format = node.get_decoration(Format)
    if not format or not format.values:
      format = cls.DEFAULT_FORMAT
    return format

  @classmethod
  def _get_parse_delegate(cls, node):  # type: (Node) -> Callable[[str], [_TYPE]]
    format = cls._get_format(node)
    if isinstance(format.values[0], str):
      # TODO (@NiklasRosenstein): Support multiple formats.
      return lambda v: datetime.datetime.strptime(v, format.values[0])
    else:
      # A format can also be an object with parse()/format() methods.
      return format.values[0].parse

  @classmethod
  def _get_format_delegate(cls, node):  # type: (Node) -> Callable[[_TYPE], [str]]
    format = cls._get_format(node)
    if isinstance(format.values[0], str):
      return lambda v: datetime.datetime.strftime(v, format.values[0])
    else:
      # A format can also be an object with parse()/format() methods.
      return format.values[0].format

  def deserialize(self, mapper, node):
    if isinstance(node.value, str):
      parse = self._get_parse_delegate(node)
      return parse(node.value)
    elif isinstance(node.value, int):
      return datetime.datetime.fromtimestamp(node.value)
    elif isinstance(node.value, self._TYPE):
      return node.value
    else:
      raise node.type_error()

  def serialize(self, mapper, node):
    if not isinstance(node.value, self._TYPE):
      raise node.type_error()
    if self.serialize_as_string:
      return self._get_format_delegate(node)(node.value)
    return node.value


@implements(IDeserializer, ISerializer)
class DateSerializer(DatetimeSerializer):

  DEFAULT_FORMAT = Format('%Y-%m-%d')
  _TYPE = datetime.date

  @classmethod
  def _get_parse_delegate(cls, node):
    fun = super(DateSerializer, self)._get_parse_delegate(node)
    def parse(v):
      result = fun(v)
      if isinstance(result, datetime.datetime):
        result = result.date()
      return result
    return parse


@implements(IDeserializer, ISerializer)
class EnumSerializer(object):
  """ Serializer for a #PythonClassType that encapsulates an #enum.Enum
  object. The serialized type for enums is a string (the enum name). """

  def deserialize(self, mapper, node):
    if not isinstance(node.value, str):
      raise node.type_error()
    try:
      return node.datatype.cls[node.value]
    except KeyError as exc:
      raise node.value_error('{!r} is not a valid enumeration value for "{}"'.format(
        node.value, node.datatype.cls.__name__))

  def serialize(self, mapper, node):
    return node.value.name


@implements(IDeserializer, ISerializer)
class PythonClassSerializer(object):
  """
  A (de-) serializer implementation for the #PythonClassType which represents
  a Python type that is not represented by any of the other #IDataType
  implementations.

  It acts as a dispatcher for the actual (de-) serialization process, which is
  determined through the following methods in order:

  1. Check if the class has a #JsonSerializer decoration.
  2. Check if there is a specific (de-) serializer registered for the wrapped
    Python type in this #PythonClassSerializer instance
  3. Check if the class has a `to_json()`/`from_json()` method.

  If the (de-) seriaization cannot be dispatched, a #SerializationTypeError is
  raised in #deserialize()/#serialize().
  """

  def deserialize(self, mapper, node):
    decoration = JsonSerializer.get(node.datatype.cls)
    deserializer = decoration.get_deserializer(node.datatype.cls) if decoration else None

    if deserializer:
      return deserializer.deserialize(mapper, node)

    to_json = getattr(node.datatype.cls, 'to_json', None)
    if to_json and callable(to_json):
      try:
        return to_json(node.datatype.value)
      except TypeError as exc:
        raise node.type_error(exc)
      except ValueError as exc:
        raise node.value_error(exc)

    raise node.type_error('Unable to find a deserializer for Python type "{}"'.format(
      node.datatype.cls.__name__))

  def serialize(self, mapper, node):
    if not isinstance(node.value, node.datatype.cls):
      raise node.value_error('Unexpected value of type "{}" found, expected "{}"'.format(
        type(node.value).__name__, node.datatype.cls.__name__))

    decoration = JsonSerializer.get(node.datatype.cls)
    serializer = decoration.get_serializer(node.datatype.cls) if decoration else None

    if serializer:
      return serializer.serialize(mapper, node)

    from_json = getattr(node.datatype.cls, 'from_json', None)
    if from_json and callable(from_json):
      try:
        return from_json(node.datatype.value)
      except TypeError as exc:
        raise node.type_error(exc)
      except ValueError as exc:
        raise node.value_error(exc)

    raise node.type_error('Unable to find a serializer for Python type "{}"'.format(
      node.datatype.cls.__name__))


@implements(IDeserializer, ISerializer)
class MultiTypeSerializer(object):

  def _do(self, method, dispatcher, node):
    errors = []
    for datatype in node.datatype.types:
      try:
        return dispatcher(node.replace(datatype=datatype))
      except SerializationTypeError as exc:
        errors.append(exc)
    error_lines = ['Unable to {} MultiType for value "{}".'.format(method, type(node.value).__name__)]
    for error in errors:
      error_lines.append('  * {}: {}'.format(
        type(error.node.datatype).__name__, error.message))
    raise node.type_error('\n'.join(error_lines))

  def deserialize(self, mapper, node):
    return self._do('deserialize', mapper.deserialize_node, node)

  def serialize(self, mapper, node):
    return self._do('serialize', mapper.serialize_node, node)


@implements(IDeserializer, ISerializer)
class UnionTypeSerializer(object):

  def deserialize(self, mapper, node):
    if not isinstance(node.value, abc.Mapping):
      raise node.type_error()

    datatype = node.datatype  # type: UnionType
    type_key = datatype.type_key
    if type_key not in node.value:
      raise node.value_error('required key "{}" not found'.format(type_key))

    type_name = node.value[type_key]
    try:
      member = datatype.type_resolver.resolve(type_name)
    except UnknownUnionTypeError:
      raise node.value_error('unknown union type: "{}"'.format(type_name))

    if datatype.nested:
      try:
        value = node.value[member.name]
      except KeyError:
        raise node.value_error('incomplete union object, missing "{}" key'.format(member.name))
      node = node.make_child(type_key, member.datatype, value)
    else:
      # Hide the type_key from the forthcoming deserialization.
      value = ChainDict({}, node.value)
      value.pop(type_key)
      node = node.replace(datatype=member.datatype, value=value)

    return mapper.deserialize_node(node)

  def serialize(self, mapper, node):
    datatype = node.datatype
    value = node.value
    try:
      member = datatype.type_resolver.reverse(value)
    except UnknownUnionTypeError as exc:
      try:
        members = datatype.type_resolver.members()
      except NotImplementedError:
        message = str(exc)
      else:
        message = 'expected {{{}}}, got {}'.format(
          '|'.join(sorted(x.type_name for x in members)),
          type(value).__name__)
      raise node.type_error(message)

    if datatype.nested:
      node = node.make_child(member.name, member.datatype, node.value)
    else:
      node = node.replace(datatype=member.datatype)

    serialized = mapper.serialize_node(node)

    result = {datatype.type_key: member.name}
    if datatype.nested:
      result[member.name] = serialized
    else:
      result.update(serialized)

    return result


@implements(IDeserializer, ISerializer)
class ProxyTypeSerializer(object):

  def deserialize(self, mapper, node):
    return context.deserialize(node.value, node.datatype.wrapped_type)

  def serialize(self, mapper, node):
    return context.serialize(node.value, node.datatype.wrapped_type)
