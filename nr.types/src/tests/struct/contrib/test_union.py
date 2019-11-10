
import pytest
from nr.types.struct import Field, Struct, JsonObjectMapper, deserialize, \
  serialize, ExtractTypeError, DefaultTypeMapper
from nr.types.struct.contrib.union import UnionType


def test_union_type():
  mapper = JsonObjectMapper()

  class Integer(Struct):
    __union_type_name__ = 'int'
    value = Field(int)
  class String(Struct):
    __union_type_name__ = 'string'
    value = Field(str)

  datatype = UnionType({'int': Integer, 'string': String})
  assert datatype == UnionType([Integer, String])

  assert deserialize(mapper, {'type': 'int', 'value': 42}, datatype) == Integer(42)
  assert deserialize(mapper, {'type': 'string', 'value': 'foo'}, datatype) == String('foo')
  with pytest.raises(ExtractTypeError):
    deserialize(mapper, {'type': 'int', 'value': 'foo'}, datatype)

  assert serialize(mapper, Integer(42), datatype) == {'type': 'int', 'value': 42}
  with pytest.raises(ExtractTypeError) as excinfo:
    serialize(mapper, 42, datatype)
  assert str(excinfo.value) == 'error in extract of value $: expected {Integer|String}, got int'

  from typing import Union
  assert datatype == DefaultTypeMapper().adapt(Union[Integer, String])
