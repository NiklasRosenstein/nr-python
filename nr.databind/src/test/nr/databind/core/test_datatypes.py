
from nr.databind.core import (
  ObjectMapper,
  SerializationTypeError,
  InvalidTypeDefinitionError,
  translate_type_def)
from nr.databind.core.datatypes import *
from nr.databind.json import JsonModule
from ..fixtures import mapper
import decimal
import pytest


def test_decimal_type(mapper):
  assert mapper.deserialize('42.0', DecimalType(float, strict=False)) == pytest.approx(42.0)
  with pytest.raises(SerializationTypeError):
    mapper.deserialize('42.0', DecimalType(float, strict=True))
  assert mapper.deserialize('42.0', DecimalType(decimal.Decimal, strict=False)) == decimal.Decimal('42.0')
  assert mapper.deserialize('42.0', DecimalType(decimal.Decimal, strict=True)) == decimal.Decimal('42.0')


def test_string_type(mapper):
  assert mapper.deserialize("foobar", StringType()) == "foobar"
  with pytest.raises(SerializationTypeError) as excinfo:
    mapper.deserialize(42, StringType(), ['a', 'b', 'c'])
  assert str(excinfo.value.location.path) == '$.a.b.c'
  assert mapper.deserialize(42, StringType(strict=False)) == "42"


def test_array_type(mapper):
  assert mapper.deserialize(["foo", "bar", "baz"], CollectionType(StringType())) == ["foo", "bar", "baz"]
  with pytest.raises(SerializationTypeError) as excinfo:
    mapper.deserialize(["foo", 42, "baz"], CollectionType(StringType()), ['a', 'b'])
  assert str(excinfo.value.location.path) == '$.a.b[1]'
  assert mapper.deserialize(["foo", 42, "baz"], CollectionType(StringType(strict=False))) == ["foo", "42", "baz"]


def test_dict_type(mapper):
  with pytest.raises(SerializationTypeError) as excinfo:
    mapper.deserialize("Hello World!", ObjectType(StringType()), ['foo'])
  assert str(excinfo.value.location.path) == '$.foo'
  assert mapper.deserialize({"msg": "Hello World!"}, ObjectType(StringType())) == {"msg": "Hello World!"}

  data =  [{"a": "b"}, {"c": "d", "e": "f"}]
  typedef = CollectionType(ObjectType(StringType()))
  assert mapper.deserialize(data, typedef) == data

  data = [{"a": "b"}, {"c": 0.2, "e": "f"}]
  typedef = CollectionType(ObjectType(StringType()))
  with pytest.raises(SerializationTypeError) as excinfo:
    mapper.deserialize(data, typedef, ['root'])
  assert str(excinfo.value.location.path) == '$.root[1].c'


def test_translate_type_def(mapper):
  assert isinstance(translate_type_def(str), StringType)
  assert isinstance(translate_type_def([str]), CollectionType)
  assert isinstance(translate_type_def([str]).item_type, StringType)
  assert isinstance(translate_type_def([]), CollectionType)
  assert isinstance(translate_type_def([]).item_type, AnyType)
  assert isinstance(translate_type_def({str}), ObjectType)
  assert isinstance(translate_type_def({str}).value_type, StringType)

  assert isinstance(translate_type_def(StringType), StringType)

  with pytest.raises(TypeError):
    translate_type_def(CollectionType)  # not enough arguments

  typedef = CollectionType(StringType())
  assert translate_type_def(typedef) is typedef


def test_translate_type_def_typing(mapper):
  from typing import List, Dict
  assert isinstance(translate_type_def(List[str]), CollectionType)
  assert isinstance(translate_type_def(List[str]).item_type, StringType)
  assert isinstance(translate_type_def(List), CollectionType)
  assert isinstance(translate_type_def(List).item_type, AnyType)
  assert isinstance(translate_type_def(Dict[str, str]), ObjectType)
  assert isinstance(translate_type_def(Dict[str, str]).value_type, StringType)
  assert isinstance(translate_type_def(Dict), ObjectType)
  assert isinstance(translate_type_def(Dict).value_type, AnyType)
  with pytest.raises(InvalidTypeDefinitionError):
    assert isinstance(translate_type_def(Dict[int, str]), PythonClassType)


def test_multitype_translation():
  type_decl = [(str, {'value_type': [str]})]
  expected_datatype = CollectionType(MultiType([
    StringType(),
    ObjectType(CollectionType(StringType()))
  ]))
  assert translate_type_def(type_decl) == expected_datatype


def test_multitype_de_serialize(mapper):
  datatype = [(str, {'value_type': [str]})]
  payload = ['a', 'b', {'c': ['e', 'f']}]

  assert mapper.deserialize(payload, datatype) == payload
  assert mapper.serialize(payload, datatype) == payload

  with pytest.raises(SerializationTypeError) as excinfo:
    payload = ['a', 'b', {'c': ['e', 'f']}, 42]
    mapper.deserialize(payload, datatype)
