
from nr.databind.core import Field, Struct
from nr.databind.json import JsonValidator, JsonFieldValidator, StructConverter
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
  class ValidateField(Struct):
    a = Field(str, JsonFieldValidator(_validate))

  mapper.deserialize({'a': 'foobar'}, ValidateField)
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
