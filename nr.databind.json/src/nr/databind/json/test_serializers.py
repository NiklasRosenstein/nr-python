
from nr.databind.core import ObjectMapper, SerializationTypeError, SerializationValueError, translate_type_def
from nr.databind.json import JsonModule, JsonSerializeCollectionAs
import pytest

try: import enum
except ImportError as exc: enum = None


@pytest.fixture
def mapper():
  return ObjectMapper(JsonModule())


def test_any_serializer(mapper):
  from nr.databind.core import AnyType

  obj = object()
  assert mapper.deserialize(obj, AnyType()) is obj
  assert mapper.serialize(obj, AnyType()) is obj


def test_string_serializer(mapper):
  from nr.databind.core import StringType

  assert mapper.deserialize('foobar', StringType()) == 'foobar'
  assert mapper.deserialize(['bar'], StringType(strict=False)) == str(['bar'])
  with pytest.raises(SerializationTypeError) as excinfo:
    mapper.deserialize(['bar'], StringType()) == str(['bar'])
  assert str(excinfo.value) == 'at $ (datatype: {}): expected "StringType", got "list"'.format(StringType())

  assert mapper.serialize('foobar', StringType()) == 'foobar'
  assert mapper.serialize(['bar'], StringType(strict=False)) == str(['bar'])
  with pytest.raises(SerializationTypeError) as excinfo:
    mapper.serialize(['bar'], StringType()) == str(['bar'])
  assert str(excinfo.value) == 'at $ (datatype: {}): expected "StringType", got "list"'.format(StringType())


def test_integer_serializer(mapper):
  from nr.databind.core import IntegerType

  assert mapper.deserialize(23, IntegerType()) == 23
  assert mapper.deserialize('23', IntegerType(strict=False)) == 23
  with pytest.raises(SerializationTypeError) as excinfo:
    mapper.deserialize('23', IntegerType())
  assert str(excinfo.value) == 'at $ (datatype: {}): expected int, got str'.format(IntegerType())

  assert mapper.serialize(23, IntegerType()) == 23
  assert mapper.serialize('23', IntegerType(strict=False)) == 23
  with pytest.raises(SerializationTypeError) as excinfo:
    mapper.serialize('23', IntegerType())
  assert str(excinfo.value) == 'at $ (datatype: {}): expected int, got str'.format(IntegerType())


def test_decimal_serializer_float(mapper):
  from nr.databind.core import DecimalType

  assert mapper.deserialize(10, DecimalType(float)) == float(10)
  assert mapper.deserialize('10.234', DecimalType(float, strict=False)) == float('10.234')
  with pytest.raises(SerializationTypeError) as excinfo:
    mapper.deserialize('10.234', DecimalType(float))
  assert str(excinfo.value) == 'at $ (datatype: {}): expected "DecimalType", got "str"'.format(DecimalType(float))

  assert mapper.serialize(10, DecimalType(float)) == float(10)
  assert mapper.serialize('10.234', DecimalType(float, strict=False)) == float('10.234')
  with pytest.raises(SerializationTypeError) as excinfo:
    mapper.serialize('10.234', DecimalType(float))
  assert str(excinfo.value) == 'at $ (datatype: {}): expected "DecimalType", got "str"'.format(DecimalType(float))


def test_decimal_serializer_decimal(mapper):
  from nr.databind.core import DecimalType
  from decimal import Decimal

  assert mapper.deserialize('10.234', DecimalType(Decimal, strict=False)) == Decimal('10.234')
  assert mapper.deserialize('10.234', DecimalType(Decimal, strict=True)) == Decimal('10.234')
  with pytest.raises(SerializationTypeError) as excinfo:
    mapper.deserialize(10, DecimalType(Decimal))
  assert str(excinfo.value) == 'at $ (datatype: {}): expected "DecimalType", got "int"'.format(DecimalType(Decimal))
  assert mapper.deserialize(10, DecimalType(Decimal, strict=False)) == Decimal('10')

  assert mapper.serialize(10, DecimalType(Decimal, strict=False)) == '10'
  assert mapper.serialize('10.234', DecimalType(Decimal, strict=False)) == '10.234'
  assert mapper.serialize(Decimal('10.234'), DecimalType(Decimal, strict=True)) == '10.234'
  with pytest.raises(SerializationTypeError) as excinfo:
    mapper.serialize('10.234', DecimalType(Decimal, strict=True))
  assert str(excinfo.value) == 'at $ (datatype: {}): expected "DecimalType", got "str"'.format(DecimalType(Decimal, strict=True))


def test_collection_serializer(mapper):
  from nr.databind.core import CollectionType, StringType
  dt = CollectionType(StringType())

  payload = ['abc', 'def']
  assert mapper.deserialize(payload, dt) == payload
  assert mapper.serialize(payload, dt) == payload
  assert mapper.serialize(payload, dt, decorations=[JsonSerializeCollectionAs(set)]) == set(payload)

  payload = ['abc', 0]
  with pytest.raises(SerializationTypeError) as excinfo:
    mapper.deserialize(payload, dt)
  assert str(excinfo.value) == 'at $[1] (datatype: {}): expected "StringType", got "int"'.format(dt.item_type)


def test_object_serializer(mapper):
  from nr.databind.core import ObjectType, StringType
  dt = ObjectType(StringType())

  payload = {'x': 'abc', 'y': 'def'}
  assert mapper.deserialize(payload, dt) == payload
  assert mapper.serialize(payload, dt) == payload

  payload = ['abc', 0]
  with pytest.raises(SerializationTypeError) as excinfo:
    mapper.deserialize(payload, dt)
  assert str(excinfo.value) == 'at $ (datatype: {}): expected "ObjectType", got "list"'.format(dt)

  payload = {'x:y': ['abc']}
  with pytest.raises(SerializationTypeError) as excinfo:
    mapper.deserialize(payload, dt)
  assert str(excinfo.value) == 'at $."x:y" (datatype: {}): expected "StringType", got "list"'.format(dt.value_type)


def test_datetime_serializer(mapper):
  from datetime import datetime
  from nr.databind.core import PythonClassType, Format
  from nr.parsing.date import Iso8601, JavaOffsetDatetime, timezone

  dt = PythonClassType(datetime)
  time = datetime.now(timezone.utc)

  # Test default (de-) serialization.
  assert mapper.deserialize(Iso8601().format(time), dt) == time
  assert mapper.serialize(time, dt) == Iso8601().format(time)

  # Test custom (de-) serialization.

  def _test_custom_format(fmt):
    if isinstance(fmt, str):
      time_s = time.strftime(fmt)
      time_v = datetime.strptime(time_s, fmt)
    else:
      time_s = fmt.format(time)
      time_v = fmt.parse(time_s)
    assert mapper.deserialize(time_s, dt, decorations=[Format(fmt)]) == time_v
    assert mapper.serialize(time_v, dt, decorations=[Format(fmt)]) == time_s

  _test_custom_format('%Y:%m:%d-%H:%M:%S')
  _test_custom_format(Iso8601())
  _test_custom_format(JavaOffsetDatetime())

  time = time.replace(tzinfo=None)
  _test_custom_format(JavaOffsetDatetime(require_timezone=False))


@pytest.mark.skipif(enum is None, reason='enum module is not available')
def test_enum_serializer(mapper):
  from nr.databind.core import PythonClassType
  from enum import Enum

  class Pet(Enum):
    CAT = 'CAT'
    DOG = 'DOG'

  dt = PythonClassType(Pet)
  assert mapper.deserialize('CAT', dt) == Pet.CAT
  assert mapper.serialize(Pet.CAT, dt) == 'CAT'

  with pytest.raises(SerializationValueError) as excinfo:
    mapper.deserialize('DOGGO', dt)
  assert str(excinfo.value) == 'at $ (datatype: {}): \'DOGGO\' is not a valid enumeration value for "Pet"'.format(dt)


def test_multitype_serializer(mapper):
  from nr.databind.core import MultiType, StringType, IntegerType, ObjectType
  dt = MultiType(IntegerType(), StringType(), ObjectType(StringType()))

  assert mapper.deserialize(42, dt) == 42
  assert mapper.deserialize('10', dt) == '10'
  assert mapper.deserialize('foobar', dt) == 'foobar'
  assert mapper.deserialize({'foo': 'bar'}, dt) == {'foo': 'bar'}
  with pytest.raises(SerializationTypeError) as excinfo:
    mapper.deserialize(['foo', 'bar'], dt)
  assert 'Unable to deserialize MultiType for value "list"' in str(excinfo.value)

  assert mapper.serialize(42, dt) == 42
  assert mapper.serialize('10', dt) == '10'
  assert mapper.serialize('foobar', dt) == 'foobar'
  assert mapper.serialize({'foo': 'bar'}, dt) == {'foo': 'bar'}
  with pytest.raises(SerializationTypeError) as excinfo:
    mapper.serialize(['foo', 'bar'], dt)
  assert 'Unable to serialize MultiType for value "list"' in str(excinfo.value)


def test_union_serializer(mapper):
  from nr.databind.core import UnionType, StructType, StringType, IntegerType, Field, Struct

  class A(Struct):
    value = Field(StringType())

  class B(Struct):
    value = Field(IntegerType())

  dt = UnionType({'a': StructType(A), 'b': StructType(B)})

  assert mapper.deserialize({'type': 'a', 'value': 'bar'}, dt) == A('bar')
  assert mapper.deserialize({'type': 'b', 'value': 42}, dt) == B(42)
  assert mapper.serialize(A('bar'), dt) == {'type': 'a', 'value': 'bar'}
  assert mapper.serialize(B(42), dt) == {'type': 'b', 'value': 42}


def test_struct_serializer(mapper):
  from nr.databind.core import Field, Struct, InheritKey, Remainder, ProxyType, SkipDefaults
  from nr.databind.json import JsonSerializer

  B = ProxyType()

  class A(Struct):
    value = Field(B)
    remainder = Field(dict(value_type=B), Remainder())

  @B.implementation
  class B(Struct):
    name = Field(str, InheritKey())
    a = Field(int, default=5)

  payload = {'value': {}, 'foo': {'a': 10}}
  obj = mapper.deserialize(payload, A)
  assert obj == A(B('value', 5), {'foo': B('foo', 10)})
  assert mapper.serialize(obj, A) == {'value': {'a': 5}, 'foo': {'a': 10}}
  assert mapper.serialize(obj, A, decorations=[SkipDefaults()]) == payload

  @JsonSerializer(deserialize='deserialize', serialize='serialize')
  class C(Struct):
    name = Field(str)

    @classmethod
    def deserialize(cls, mapper, node):
      if isinstance(node.value, str):
        return cls(node.value)
      raise NotImplementedError

    @classmethod
    def serialize(cls, mapper, node):
      return node.value.name

  assert mapper.deserialize({'name': 'foo'}, C) == C('foo')
  assert mapper.deserialize('bar', C) == C('bar')
  with pytest.raises(SerializationTypeError) as excinfo:
    mapper.deserialize(1, C)
  assert str(excinfo.value) == 'at $ (datatype: {}): expected "C", got "int"'.format(translate_type_def(C))

  assert mapper.serialize(C('foo'), C) == 'foo'

  @SkipDefaults()
  class D(Struct):
    name = Field(str)
    age = Field(int, default=42)

  assert mapper.serialize(D('John', 30), D) == {'name': 'John', 'age': 30}
  assert mapper.serialize(D('John', 42), D) == {'name': 'John'}

def test_struct_serializer_raw(mapper):
  from nr.databind.core import Field, Struct, StringType, Raw

  class A(Struct):
    name = Field(str)

  class B(Struct):
    a = Field(A)
    raw_data = Field({}, Raw())

  payload = {'a': {'name': 'Foo Bar'}, 'b': 42}
  obj = mapper.deserialize(payload, B)
  assert obj == B(A('Foo Bar'), payload)
  assert mapper.serialize(obj, B) == {'a': {'name': 'Foo Bar'}}


def test_store_node_decoration(mapper):
  from nr.databind.core import Collection, Field, Struct, StringType, StoreNode

  class I(Collection, list):
    item_type = StringType()

  class A(Struct):
    items = Field(I, StoreNode())

  payload = {'items': ['a', 'b', 'c']}

  obj = mapper.deserialize(payload, A)
  assert obj.__databind__ == {'mapper': mapper}
  assert obj.items.__databind__['node'].result is obj.items
  assert obj.items.__databind__['node'].value is payload['items']

  obj = mapper.deserialize(payload, A, decorations=[StoreNode()])
  assert obj.__databind__['node'].value is payload
  assert obj.items.__databind__['node'].result is obj.items
  assert obj.items.__databind__['node'].value is payload['items']


def test_context_collect(mapper):
  from nr.databind.core import StringType, Collect

  collect = Collect()
  mapper.deserialize('foo', StringType(), decorations=[collect])
  assert len(collect.nodes) == 1
  assert collect.nodes[0].value == 'foo'
  assert collect.nodes[0].result == 'foo'


def test_serialize_as(mapper):
  from nr.databind.core import SerializeAs, StringType

  @SerializeAs(StringType())
  class Foo(object):
    pass

  assert mapper.deserialize('foo', Foo) == 'foo'
  with pytest.raises(SerializationTypeError) as excinfo:
    mapper.deserialize(10, Foo)
  assert str(excinfo.value) == 'at $ (datatype: {}): expected "StringType", got "int"'.format(StringType())


  assert mapper.serialize('foo', Foo) == 'foo'
  with pytest.raises(SerializationTypeError) as excinfo:
    mapper.serialize(10, Foo)
  assert str(excinfo.value) == 'at $ (datatype: {}): expected "StringType", got "int"'.format(StringType())
