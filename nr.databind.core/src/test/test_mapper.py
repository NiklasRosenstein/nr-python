
from nr.databind.core import (ObjectMapper, IntegerType, IDeserializer, ISerializer,
  SerializationTypeError, SerializationValueError)
from nr.interface import implements
import pytest


@implements(IDeserializer, ISerializer)
class IntegerToStringSerializer(object):

  def deserialize(self, mapper, node):
    if not isinstance(node.value, str):
      raise node.type_error('expected str, got "{}"'.format(type(node.value).__name__))
    try:
      return int(node.value)
    except ValueError as exc:
      raise node.value_error(exc)

  def serialize(self, mapper, node):
    if not isinstance(node.value, int):
      raise node.type_error('expected int, got "{}"'.format(type(node.value).__name__))
    return str(node.value)


@pytest.fixture
def mapper():
  mapper = ObjectMapper()
  mapper.register(IntegerType, IntegerToStringSerializer())
  return mapper


def test_deserialize(mapper):
  assert mapper.deserialize('42', IntegerType) == 42

  with pytest.raises(SerializationTypeError) as excinfo:
    mapper.deserialize(['42'], IntegerType)
  assert str(excinfo.value) == 'at $: expected str, got "list"'

  with pytest.raises(SerializationValueError) as excinfo:
    mapper.deserialize('not an int', IntegerType)
  assert str(excinfo.value) == 'at $: invalid literal for int() with base 10: \'not an int\''


def test_serialize(mapper):
  assert mapper.serialize(42, IntegerType) == '42'

  with pytest.raises(SerializationTypeError) as excinfo:
    mapper.serialize([42], IntegerType)
  assert str(excinfo.value) == 'at $: expected int, got "list"'
