
from nr.databind.core import (
  Field,
  Struct,
  SerializationTypeError,
  UnionType,
  translate_type_def)
from ..fixtures import mapper
import pytest


def test_union_type(mapper):

  class Integer(Struct):
    __union_type_name__ = 'int'
    value = Field(int)

  class String(Struct):
    __union_type_name__ = 'string'
    value = Field(str)

  datatype = UnionType({'int': Integer, 'string': String})
  assert datatype == UnionType([Integer, String])

  assert mapper.deserialize({'type': 'int', 'value': 42}, datatype) == Integer(42)
  assert mapper.deserialize({'type': 'string', 'value': 'foo'}, datatype) == String('foo')
  with pytest.raises(SerializationTypeError):
    mapper.deserialize({'type': 'int', 'value': 'foo'}, datatype)

  assert mapper.serialize(Integer(42), datatype) == {'type': 'int', 'value': 42}
  with pytest.raises(SerializationTypeError) as excinfo:
    mapper.serialize(42, datatype)
  assert str(excinfo.value) == 'at $: expected {Integer|String}, got int'

  from typing import Union
  assert datatype == translate_type_def(Union[Integer, String])
