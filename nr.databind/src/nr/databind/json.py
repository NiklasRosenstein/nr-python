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
Converts from and to JSON like nested structures.
"""

from __future__ import absolute_import
from functools import partial
from nr.collections import ChainDict
from nr.pylang.utils import NotSet
from nr.pylang.utils import classdef
from nr.collections import abc, OrderedDict
from nr.interface import implements
from nr.parsing.date import ISO_8601
from .core.collection import Collection
from .core.datatypes import (
  AnyType,
  BooleanType,
  StringType,
  IntegerType,
  DecimalType,
  CollectionType,
  ObjectType,
  DatetimeType,
  DateType,
  PythonClassType,
  MultiType,
  translate_type_def)
from .core.decoration import (
  get_decoration,
  collect_metadata,
  Decoration,
  ClassDecoration)
from .core.errors import (
  SerializationTypeError,
  SerializationValueError,
  InvalidTypeDefinitionError)
from .core.interfaces import IDeserializer, ISerializer
from .core.mapper import SimpleModule, ObjectMapper
from .core.struct import StructType
from .core.union import UnionType, UnknownUnionTypeError
import datetime
import decimal
import inspect
import six
import json


__all__ = [
  'JsonModule',
  'JsonFieldName',
  'JsonRequired',
  'JsonDeserializer',
  'JsonSerializer',
  'JsonStrict',
  'JsonValidator',
  'JsonEncoder']


class JsonModule(SimpleModule):

  def __init__(self):
    super(JsonModule, self).__init__()
    try: import enum
    except ImportError: enum = None
    else:
      self.register_duplex(enum.Enum, EnumConverter())

    self.register_duplex(AnyType, AnyConverter())
    self.register_duplex(BooleanType, BooleanConverter())
    self.register_duplex(StringType, StringConverter())
    self.register_duplex(IntegerType, IntegerConverter())
    self.register_duplex(DecimalType, DecimalConverter())
    self.register_duplex(CollectionType, CollectionConverter())
    self.register_duplex(ObjectType, ObjectConverter())
    self.register_duplex(StructType, StructConverter())
    self.register_duplex(DatetimeType, DatetimeConverter())
    self.register_duplex(DateType, DateConverter())
    self.register_duplex(PythonClassType, PythonClassConverter())
    self.register_duplex(MultiType, MultiTypeConverter())
    self.register_duplex(UnionType, UnionTypeConverter())


@implements(IDeserializer, ISerializer)
class AnyConverter(object):

  def deserialize(self, context, location):
    return location.value

  def serialize(self, context, location):
    return location.value


@implements(IDeserializer, ISerializer)
class BooleanConverter(object):

  def deserialize(self, context, location):
    if isinstance(location.value, bool):
      return location.value
    raise SerializationTypeError(location)

  def serialize(self, context, location):
    if location.datatype.strict and not isinstance(location.value, bool):
      raise SerializationTypeError(location)
    return bool(location.value)


@implements(IDeserializer, ISerializer)
class StringConverter(object):

  def deserialize(self, context, location):
    if isinstance(location.value, six.string_types):
      return location.value
    if location.datatype.strict:
      raise SerializationTypeError(location)
    return str(location.value)

  def serialize(self, context, location):
    return location.value


@implements(IDeserializer, ISerializer)
class IntegerConverter(object):

  def deserialize(self, context, location):
    try:
      return location.datatype.check_value(location.value)
    except TypeError as exc:
      raise SerializationTypeError(location, exc)

  def serialize(self, context, location):
    return self.deserialize(context, location)


@implements(IDeserializer, ISerializer)
class DecimalConverter(object):

  def __init__(self, supports_decimal=False, as_string=None):
    super(DecimalConverter, self).__init__()
    self.supports_decimal = supports_decimal
    self.as_string = as_string

  def deserialize(self, context, location):
    if isinstance(location.value, location.datatype.accepted_input_types):
      return location.datatype.coerce(location.value)
    raise SerializationTypeError(location)

  def serialize(self, context, location):
    value = location.datatype.coerce(location.value)
    is_decimal = isinstance(location.value, decimal.Decimal)

    if self.supports_decimal and self.as_string is None and is_decimal:
      return value
    if self.as_string or (self.as_string is None and is_decimal):
      return str(value)
    return float(value)


@implements(IDeserializer, ISerializer)
class CollectionConverter(object):
  """
  Serializes the [[CollectionType]] from a Python collection object to a
  list (for serialization in JSON). If the underlying Python type is
  unordered, the values will be sorted by their hash.
  """

  def deserialize(self, context, location):
    # Check if the value we receive is actually a collection.
    try:
      location.datatype.check_value(location.value, _convert=False)
    except TypeError:
      raise SerializationTypeError(location)

    # Deserialize child elements.
    item_type = location.datatype.item_type
    result = []
    for index, item in enumerate(location.value):
      result.append(context.deserialize(item, item_type, index))

    # Convert to the designated Python type.
    py_type = location.datatype.py_type
    if not isinstance(py_type, type) or not isinstance(result, py_type):
      result = py_type(result)

    if isinstance(result, Collection):
      result.__databind__ = {}
      collect_metadata(result.__databind__, context, location, py_type, context)

    return result

  def serialize(self, context, location):
    # Check if the value we receive is actually a collection.
    try:
      location.datatype.check_value(location.value, _convert=False)
    except TypeError:
      raise SerializationTypeError(location)

    # Serialize child elements.
    item_type = location.datatype.item_type
    result = []
    for index, item in enumerate(location.value):
      result.append(context.serialize(item, item_type, index))

    # Convert to the designated JSON type.
    serialize_as = get_decoration(JsonSerializeFieldAs, location, context)
    json_type = serialize_as.cls if serialize_as else list
    if not isinstance(json_type, type) or not isinstance(result, json_type):
      result = json_type(result)

    return result


@implements(IDeserializer, ISerializer)
class ObjectConverter(object):

  def deserialize(self, context, location):
    if not isinstance(location.value, dict):
      raise SerializationTypeError(location)
    value_type = location.datatype.value_type
    result = location.datatype.py_type()
    for key in location.value:
      result[key] = context.deserialize(location.value[key], value_type, key)
    return result

  def serialize(self, context, location):
    serialize_as = get_decoration(JsonSerializeFieldAs, location, context)
    result = serialize_as.cls() if serialize_as else {}
    value_type = location.datatype.value_type
    for key in location.value:
      result[key] = context.serialize(location.value[key], value_type, key)
    return result


@implements(IDeserializer, ISerializer)
class StructConverter(object):

  class SerializeSkipDefaultValues(Decoration):
    """ This decoration serves as a flag to indicate that during serialization
    an optional field should be skipped if its value matches the default value.
    The default value for this is #True. This decoration is checked on the
    Struct class and the context. """

    classdef.comparable(['enabled'])
    classdef.repr(['enabled'])

    def __init__(self, enabled=True):
      self.enabled = enabled

  def _extract_kwargs(self, field, context, struct_cls, location, kwargs, handled_keys):
    assert field.name not in kwargs, (field, struct_cls, location)

    json_object_key = get_decoration(JsonObjectKey, field)
    if json_object_key:
      kwargs[field.name] = location.path[-1]
      return

    json_remainder = get_decoration(JsonRemainder, field)
    if json_remainder:
      if not isinstance(field.datatype, ObjectType):
        raise RuntimeError('"{}.{}" expected ObjectType due to JsonRemainder '
          'decoration, got {}'.format(struct_cls.__name__, field.name,
            type(location.datatype).__name__))
      result = {}
      for key in location.value:
        if key not in handled_keys:
          result[key] = context.deserialize(location.value[key],
            field.datatype.value_type, key, decorations=field.decorations)
          handled_keys.add(key)
      kwargs[field.name] = result
      return

    # Retrieve decorations that will affect the deserialization of this field.
    json_default = get_decoration(JsonDefault, field)
    json_required = get_decoration(JsonRequired, field)
    json_field_name = get_decoration(JsonFieldName, field)
    json_field_validator = get_decoration(JsonFieldValidator, field)

    key = json_field_name.name if json_field_name else field.name
    if key not in location.value:
      if json_required or (field.default is NotSet and not json_default):
        msg = 'member "{}" is missing for {} object'.format(key, struct_cls.__name__)
        raise SerializationValueError(location, msg)
      if json_default:
        value = json_default.value
      else:
        return
    else:
      value = location.value[key]

    if field.nullable and value is None:
      kwargs[field.name] = None
    else:
      kwargs[field.name] = context.deserialize(value, field.datatype, key,
        decorations=field.decorations)

    if json_field_validator:
      kwargs[field.name] = json_field_validator(kwargs[field.name])

    handled_keys.add(key)

  def deserialize(self, context, location):
    # Check if there is a custom deserializer on the struct class.
    struct_cls = location.datatype.struct_cls
    deserializer = get_decoration(JsonDeserializer, struct_cls)
    if deserializer:
      try:
        obj = deserializer(context, location)
      except NotImplementedError:
        deserializer = None

    if not deserializer:
      obj = self._deserialize(context, location)

    if obj.__databind__ is None:
      obj.__databind__ = {}
    collect_metadata(obj.__databind__, context, location, struct_cls, context)

    validator = get_decoration(JsonValidator, struct_cls)
    if validator:
      try:
        validator(obj)
      except ValueError as exc:
        raise SerializationValueError(location, exc)
      except TypeError as exc:
        raise SerializationTypeError(location, exc)

    return obj

  def _deserialize(self, context, location):
    struct_cls = location.datatype.struct_cls

    # Otherwise, we expect a mapping.
    if not isinstance(location.value, abc.Mapping):
      raise SerializationTypeError(location)

    fields = struct_cls.__fields__
    strict = get_decoration(JsonStrict, struct_cls, context)
    store_remaining_keys = get_decoration(JsonStoreRemainingKeys, struct_cls, context)

    kwargs = {}
    handled_keys = set(location.datatype.ignore_keys)
    remainder_fields = []
    for name, field in fields.items().sortby(lambda x: x[1].get_priority()):
      if field.hidden:
        continue
      if get_decoration(field, JsonRemainder):
        remainder_fields.append(field)
        continue
      assert name == field.name, "woops: {}".format((name, field))
      self._extract_kwargs(field, context, struct_cls, location, kwargs, handled_keys)

    for field in remainder_fields:
      self._extract_kwargs(field, context, struct_cls, location, kwargs, handled_keys)

    if strict or store_remaining_keys:
      remaining_keys = set(location.value.keys()) - handled_keys
      if remaining_keys and strict:
        raise SerializationValueError(location, "strict object type \"{}\" does not "
          "allow additional keys on extract, but found {!r}".format(
            struct_cls.__name__, remaining_keys))

    obj = object.__new__(struct_cls)
    obj.__databind__ = {}

    try:
      obj.__init__(**kwargs)
    except TypeError as exc:
      raise SerializationTypeError(location, exc)

    if store_remaining_keys:
      obj.__databind__[store_remaining_keys.field_name] = remaining_keys

    return obj

  def serialize(self, context, location):
    struct_cls = location.datatype.struct_cls
    if not isinstance(location.value, struct_cls):
      raise SerializationTypeError(location)

    # Check if there is a custom serializer on the struct class.
    serializer = get_decoration(JsonSerializer, struct_cls)
    if serializer:
      try:
        result = serializer(context, location)
      except NotImplementedError:
        serializer = None

    if not serializer:
      skip_default_values = get_decoration(self.SerializeSkipDefaultValues,
        location, struct_cls, context) or self.SerializeSkipDefaultValues(True)
      serialize_as = get_decoration(JsonSerializeAs, struct_cls, location, context)
      result = serialize_as.cls() if serialize_as else {}
      for name, field in struct_cls.__fields__.items():
        if field.hidden:
          continue

        value = getattr(location.value, name)
        if not (field.nullable and value is None):
          value = context.serialize(value, field.datatype, name,
            decorations=field.decorations)

        if field.default is not NotSet and skip_default_values.enabled and \
            value == field.get_default_value():
          continue

        json_field_name = get_decoration(JsonFieldName, field)
        key = json_field_name.name if json_field_name else field.name
        result[key] = value

    return result


@implements(IDeserializer, ISerializer)
class DatetimeConverter(object):

  DEFAULT_FORMAT = DatetimeType.Format(ISO_8601)

  @classmethod
  def _get_format(cls, context, location):
    format = get_decoration(type(cls.DEFAULT_FORMAT), location, context)
    if not format or not format.formats:
      format = cls.DEFAULT_FORMAT
    return format

  @classmethod
  def _get_parse_delegate(cls, context, location):
    format = cls._get_format(context, location)
    if isinstance(format.formats[0], str):
      return lambda v: datetime.datetime.strptime(v, format.formats[0])
    else:
      # A format can also be an object with parse()/format() methods.
      return format.formats[0].parse

  @classmethod
  def _get_format_delegate(cls, context, location):
    format = cls._get_format(context, location)
    if isinstance(format.formats[0], str):
      return lambda v: datetime.datetime.strftime(v, format.formats[0])
    else:
      # A format can also be an object with parse()/format() methods.
      return format.formats[0].format

  def deserialize(self, context, location):
    if isinstance(location.value, str):
      parse = self._get_parse_delegate(context, location)
      return parse(location.value)
    elif isinstance(location.value, int):
      return datetime.datetime.fromtimestamp(location.value)
    elif isinstance(location.value, datetime.datetime):
      return location.value
    else:
      raise SerializationTypeError(location)

  def serialize(self, context, location):
    if isinstance(location.value, datetime.datetime):
      format_ = self._get_format_delegate(context, location)
      return format_(location.value)
    raise SerializationTypeError(location)


@implements(IDeserializer, ISerializer)
class DateConverter(DatetimeConverter):

  DEFAULT_FORMAT = DateType.Format('%Y-%m-%d')

  def __init__(self, serialize_as_date=False):
    self.serialize_as_date = False

  def deserialize(self, context, location):
    if isinstance(location.value, str):
      parse = self._get_parse_delegate(context, location)
      value = parse(location.value)
      if isinstance(value, datetime.datetime):
        value = value.date()
      return value
    elif isinstance(location.value, int):
      return datetime.datetime.fromtimestamp(location.value).date()
    elif isinstance(location.value, datetime.date):
      return location.value
    else:
      raise SerializationTypeError(location)

  def serialize(self, context, location):
    if not isinstance(location.value, datetime.date):
      raise SerializationTypeError(location)
    if self.serialize_as_date:
      return location.value
    format = self._get_format_delegate(context, location)
    return format(location.value)


@implements(IDeserializer, ISerializer)
class EnumConverter(object):
  """ Converter for a #PythonClassType that encapsulates an #enum.Enum
  object. The serialized type for enums is a string (the enum name). """

  def deserialize(self, context, location):
    try:
      return location.datatype.cls[location.value]
    except KeyError as exc:
      raise SerializationValueError(location, exc)

  def serialize(self, context, location):
    return location.value.name


@implements(IDeserializer, ISerializer)
class PythonClassConverter(object):
  """ Uses the #to_json()/#from_json() method that is defined on the class
  to serialize/deserialize the object. Raises a #SerializationTypeError if
  the class does not support it. """

  def deserialize(self, context, location):
    deserializer = get_decoration(JsonDeserializer, location.datatype.cls)
    if not deserializer:
      raise SerializationTypeError(location, 'No JsonDeserializer found '
        'on class {}'.format(location.datatype.cls.__name__))
    return deserializer(context, location)

  def serialize(self, context, location):
    deserializer = get_decoration(JsonSerializer, location.datatype.cls)
    if not serializer:
      raise SerializationTypeError(location, 'No JsonSerializer found '
        'on class {}'.format(location.datatype.cls.__name__))
    if not isinstance(location.value, location.datatype.cls):
      raise SerializationValueError(location, 'Expected {} instance, got {}'
        .format(location.datatype.cls.__name__, type(location.value).__name__))
    return serializer(context, location)


@implements(IDeserializer, ISerializer)
class MultiTypeConverter(object):

  def _do(self, context, location, method):
    errors = []
    for datatype in location.datatype.types:
      try:
        return getattr(context, method)(location.value, datatype)
      except SerializationTypeError as exc:
        errors.append(exc)
    error_lines = ['Unable to {} MultiType for value "{}".'.format(method, type(location.value).__name__)]
    for error in errors:
      error_lines.append('  * {}: {}'.format(
        type(error.location.datatype).__name__, error.message))
    raise SerializationTypeError(location, '\n'.join(error_lines))

  def deserialize(self, context, location):
    return self._do(context, location, 'deserialize')

  def serialize(self, context, location):
    return self._do(context, location, 'serialize')


@implements(IDeserializer, ISerializer)
class UnionTypeConverter(object):

  def deserialize(self, context, location):
    if not isinstance(location.value, abc.Mapping):
      raise SerializationTypeError(location)

    datatype = location.datatype  # type: UnionType
    type_key = datatype.type_key
    if type_key not in location.value:
      raise SerializationValueError(location,
        'required key "{}" not found'.format(type_key))

    type_name = location.value[type_key]
    try:
      member = datatype.type_resolver.resolve(type_name)
    except UnknownUnionTypeError:
      raise SerializationValueError(location,
        'unknown union type: "{}"'.format(type_name))

    if datatype.nested:
      value = location.value[member.name]
      key = type_key
    else:
      # Hide the type_key from the forthcoming deserialization.
      value = ChainDict({}, location.value)
      value.pop(type_key)
      key = None

    return context.deserialize(value, member.datatype, key)

  def serialize(self, context, location):
    datatype = location.datatype
    value = location.value
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
      raise SerializationTypeError(location, message)

    result = {datatype.type_key: member.name}
    if datatype.nested:
      result[member.name] = context.serialize(
        location.value, member.datatype, member.name)
    else:
      result.update(context.serialize(location.value, member.datatype, None))

    return result


class JsonDecoration(Decoration):
  pass


class JsonFieldName(JsonDecoration):
  """ A decoration to define the name of a field in a JSON payload. """

  classdef.repr('name')

  def __init__(self, name):
    self.name = name


class JsonDefault(JsonDecoration):
  """ A decoration that overrides the default value of a field when it is
  deserialized from JSON. The value specified here is deserialized in place.
  """

  def __init__(self, value):
    self.value = value

  def __repr__(self):
    return 'JsonDecoration(value={!r})'.format(self.value)


class JsonRequired(JsonDecoration):
  """ A decorator that defines if a JSON field is required. By default, a
  field that has a default value does not need to be specified in the JSON
  payload. If this decoration exists on a field, it is always required. """

  classdef.repr([])


class JsonDeserializer(ClassDecoration, JsonDecoration):
  """ A class decoration that defines the deserializer that is to be used
  for the class. Can also be used to decorate methods that implementation
  the deserialization inside the class. """

  def __init__(self, deserializer):  # type: (Callable, IDeserializer)
    if inspect.isfunction(deserializer):
      deserializer = IDeserializer(deserializer)
    if not IDeserializer.provided_by(deserializer):
      raise TypeError('expected IDeserializer, got {}'.format(
        type(deserializer).__name__))
    self.deserializer = deserializer

  def __call__(self, context, location):
    try:
      return self.deserializer.deserialize(context, location)
    except ValueError as exc:
      raise SerializationValueError(location, exc)
    except TypeError as exc:
      raise SerializationTypeError(location, exc)


class JsonSerializer(ClassDecoration, JsonDecoration):
  """ A class decoration that defines the deserializer that is to be used
  for the class. Can also be used to decorate methods that implementation
  the deserialization inside the class. """

  def __init__(self, serializer):  # type: (Union[Callable, IDeserializer])
    if inspect.isfunction(serializer):
      serializer = ISerializer(serializer)
    if not ISerializer.provided_by(serializer):
      raise TypeError('expected ISerializer, got {}'.format(
        type(serializer).__name__))
    self.serializer = serializer

  def __call__(self, context, location):
    try:
      return self.serializer.serialize(context, location)
    except ValueError as exc:
      raise SerializationValueError(location, exc)
    except TypeError as exc:
      raise SerializationTypeError(location, exc)


class JsonSerializeFieldAs(JsonDecoration):
  """ This decoration describes the type as which a value should be
  serialized as. The default for this is the standard Python dictionary,
  but for some use cases this may need to be changed to a different mapping
  type. Note that this is not respected by all serializers but only for those
  that convert to collection types (eg. #ObjectConverter, #StructConverter and
  #CollectionConverter). """

  classdef.comparable(['cls'])
  classdef.repr(['cls'])

  def __init__(self, cls=dict):
    self.cls = cls


class JsonSerializeAs(JsonSerializeFieldAs, ClassDecoration):
  pass


class JsonStrict(ClassDecoration, JsonDecoration):
  """ A decoration that causes the #StructConverter to raise an exception for
  unhandled keys during deserialization. """

  classdef.comparable([])
  classdef.repr([])


class JsonStoreRemainingKeys(ClassDecoration, JsonDecoration):
  """ A decoration that causes a #StructConverter to add a `remaining_keys`
  metadata field for the keys that have not been handled during the
  deserialization. """

  classdef.comparable('field_name')
  classdef.repr('field_name')

  def __init__(self, field_name='remaining_keys'):
    self.field_name = field_name

  def iter_paths(self, obj, expect_has_metadata=False, _path=None):
    # type: (Struct, Optional[MutablePath]) -> Iterable[Path]
    """ Yields a #Path for every key that is unhandled, starting from #obj. """

    from .core.location import MutablePath
    from .core.struct import Struct

    if not isinstance(obj, Struct):
      raise TypeError('expected Struct, got {}'.format(type(obj).__name__))
    if _path is None:
      _path = MutablePath([])
    fallback = (None if expect_has_metadata else set())
    for key in obj.__databind__.get(self.field_name, fallback):
      yield _path.to_immutable(key)
    for field in obj.__fields__.values():
      value = getattr(obj, field.name)
      if isinstance(value, Struct):
        _path.push(field.name)
        for _ in self.iter_paths(getattr(obj, field.name), expect_has_metadata, _path):
          yield _
        _path.pop()


class JsonValidator(ClassDecoration, JsonDecoration):
  """ A class decoration for a validation function that is called after
  a #Struct has been deserialized. """

  def __init__(self, validator):
    assert callable(validator), 'expected callable for JsonValidator'
    self._validator = validator
    super(JsonValidator, self).__init__()

  def __populate__(self):
    return self._validator

  def __call__(self, instance):
    self._validator(instance)


class JsonFieldValidator(JsonDecoration):
  """ A decoration for a field validation function. Validators must return
  the validated value. """

  def __init__(self, validator):
    assert callable(validator), 'expected callable for JsonFieldValidator'
    self._validator = validator
    super(JsonFieldValidator, self).__init__()

  def __call__(self, value):
    return self._validator(value)


class JsonMixin(object):
  """ A mixin for #Struct or #Collection subclasses that adds #to_json()
  and #from_json() methods which de/serialize an instance of the class with
  an #ObjectMapper and the #JsonModule. """

  def to_json(self, *args, **kwargs):
    mapper = ObjectMapper(JsonModule())
    return mapper.serialize(self, type(self), *args, **kwargs)

  @classmethod
  def from_json(cls, data, *args, **kwargs):
    mapper = ObjectMapper(JsonModule())
    return mapper.deserialize(data, cls, *args, **kwargs)


class JsonEncoder(json.JSONEncoder):
  """ A #json.JSONEncoder that supports serializing objects into JSON from
  their Python type via an #ObjectMapper. """

  def __init__(self, mapper):
    super(JsonEncoder, self).__init__()
    self._mapper = mapper

  def default(self, obj):
    try:
      datatype = translate_type_def(type(obj))
    except InvalidTypeDefinitionError:
      pass
    else:
      return self._mapper.serialize(obj, datatype)
    return super(JsonEncoder, self).default(obj)


class JsonObjectKey(JsonDecoration):
  """ Decoration for a field to indicate that its value should be derived
  from the key that the deserialized object is associated with in the parent
  structure. """


class JsonRemainder(JsonDecoration):
  """ Decoration for an #ObjectType field to indicate that its values should
  be filled with the remaining keys from the struct deserialization. """
