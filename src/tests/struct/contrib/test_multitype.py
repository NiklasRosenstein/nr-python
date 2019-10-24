
import pytest

from nr.types.struct import JsonObjectMapper, deserialize, serialize, \
  get_type_mapper, CollectionType, StringType, ObjectType, ExtractTypeError
from nr.types.struct.contrib.multitype import MultiType


def test_multitype():
  datatype = CollectionType(MultiType([
    StringType(),
    ObjectType(CollectionType(StringType()))
  ]))

  payload = ['a', 'b', {'c': ['e', 'f']}]
  assert deserialize(JsonObjectMapper(), payload, datatype) == payload
  assert serialize(JsonObjectMapper(), payload, datatype) == payload

  with pytest.raises(ExtractTypeError) as excinfo:
    payload = ['a', 'b', {'c': ['e', 'f']}, 42]
    deserialize(JsonObjectMapper(), payload, datatype)
