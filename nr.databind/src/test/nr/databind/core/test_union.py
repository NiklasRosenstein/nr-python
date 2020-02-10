
from nr.databind.core import (
  Field,
  Struct,
  SerializationValueError,
  SerializationTypeError,
  UnionType,
  translate_type_def)
from nr.databind.json import JsonStrict
from typing import Union
from ..fixtures import mapper
import pytest

class Integer(Struct):
  __union_type_name__ = 'int'
  value = Field(int)


class String(Struct):
  __union_type_name__ = 'string'
  value = Field(str)


datatype = UnionType({'int': Integer, 'string': String})


def test_union_constructor():
  assert datatype == UnionType([Integer, String])


def test_union_type_conversion():
  assert datatype == translate_type_def(Union[Integer, String])


def test_union_standard_type_resolver(mapper):
  payload = {'type': 'int', 'value': 42}
  obj = mapper.deserialize(payload, datatype)
  assert obj == Integer(42)
  assert mapper.serialize(obj, datatype) == payload

  assert mapper.deserialize({'type': 'string', 'value': 'foo'}, datatype) == String('foo')
  with pytest.raises(SerializationTypeError):
    mapper.deserialize({'type': 'int', 'value': 'foo'}, datatype)

  assert mapper.serialize(Integer(42), datatype) == {'type': 'int', 'value': 42}
  with pytest.raises(SerializationTypeError) as excinfo:
    mapper.serialize(42, datatype)
  assert str(excinfo.value) == 'at $: expected {Integer|String}, got int'


class _Struct1(Struct):
  value = Field(str)


class _Struct2(_Struct1):
  cls = Field(str)


def test_union_import_type_resolver(mapper):
  union_type = UnionType.with_import_resolver(type_key='cls')

  payload = {'cls': 'test.nr.databind.core.test_union._Struct1', 'value': 'foo'}
  obj = mapper.deserialize(payload, union_type)
  assert obj == _Struct1('foo')
  assert mapper.serialize(obj, union_type) == payload

  # Strict deserialization must work as well (the "cls" must not be present
  # when deserializing the imported type.
  payload = {'cls': 'test.nr.databind.core.test_union._Struct1', 'value': 'foo'}
  obj = mapper.deserialize(payload, union_type, decorations=[JsonStrict()])
  assert obj == _Struct1('foo')
  assert mapper.serialize(obj, union_type) == payload

  # Deserializing the TestStructWithClsField should not work because the
  # "cls" field is not propagated when deserializing the type.
  payload = {'cls': 'test.nr.databind.core.test_union._Struct2', 'value': 'foo'}
  with pytest.raises(SerializationValueError) as excinfo:
    mapper.deserialize(payload, union_type)
  assert str(excinfo.value) == 'at $: member "cls" is missing for _Struct2 object'


def test_union_import_type_builtins(mapper):
  union_type = UnionType.with_import_resolver(nested=True)

  payload = mapper.serialize(42, union_type)
  assert payload == {'type': 'builtins.int', 'builtins.int': 42}
  assert mapper.deserialize(payload, union_type) == 42
