
from nr.databind.core import Field, Struct
from nr.databind.json import (
  JsonValidator,
  JsonFieldValidator,
  JsonSerializeAs,
  JsonSerializeFieldAs,
  StructConverter)
from ..fixtures import mapper
import pytest


def test_json_validator(mapper):

  class ValidateCalled(Exception):
    pass

  class ValidateStruct(Struct):
    a = Field(str)
    @JsonValidator
    def __validate(self):
      if self.a == 'fail':
        raise Exception('fail!')

  mapper.deserialize({'a': 'foobar'}, ValidateStruct)
  with pytest.raises(Exception) as excinfo:
    mapper.deserialize({'a': 'fail'}, ValidateStruct)
  assert str(excinfo.value) == 'fail!'

  def _validate(value):
    if value == 'fail':
      raise Exception('fail!')
    return value
  class ValidateField(Struct):
    a = Field(str, JsonFieldValidator(_validate))

  assert mapper.deserialize({'a': 'foobar'}, ValidateField) == ValidateField('foobar')
  with pytest.raises(Exception) as excinfo:
    mapper.deserialize({'a': 'fail'}, ValidateField)
  assert str(excinfo.value) == 'fail!'


def test_serialize_skip_default_values(mapper):
  class Test(Struct):
    a = Field(str, default='foo')

  assert mapper.serialize(Test(), Test) == {}
  assert mapper.serialize(Test('bar'), Test) == {'a': 'bar'}
  assert mapper.serialize(Test(), Test, decorations=[StructConverter.SerializeSkipDefaultValues(False)]) == {'a': 'foo'}
  assert mapper.serialize(Test('bar'), Test, decorations=[StructConverter.SerializeSkipDefaultValues(False)]) == {'a': 'bar'}


class CustomCollection(object):
  def __init__(self, data=None):
    self.data = data or list(data)
  def __eq__(self, other):
    if isinstance(other, CustomCollection):
      return self.data == other.data
    return False


class CustomMapping(object):
  def __init__(self, data=None):
    self.data = data or {}
  def __setitem__(self, key, value):
    self.data[key] = value
  def __eq__(self, other):
    if isinstance(other, CustomMapping):
      return self.data == other.data
    return False


def test_struct_serialize_as(mapper):
  class Test(Struct):
    a = Field(str)
    JsonSerializeAs(CustomMapping)
  payload = mapper.serialize(Test('foo'), Test)
  assert payload == CustomMapping({'a': 'foo'})


def test_object_serialize_as(mapper):

  class Test(Struct):
    a = Field(dict, JsonSerializeFieldAs(CustomMapping))
  payload = mapper.serialize(Test({'hello': 'world'}), Test)
  assert payload == {'a': CustomMapping({'hello': 'world'})}


def test_collection_serialize_as(mapper):
  class Test(Struct):
    a = Field(list, JsonSerializeFieldAs(CustomCollection))
  payload = mapper.serialize(Test(['a', 'be', 'cee']), Test)
  assert payload == {'a': CustomCollection(['a', 'be', 'cee'])}
