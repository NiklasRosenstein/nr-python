
from nr.databind.core import Field, Struct
from nr.databind.json import JsonValidator, JsonFieldValidator
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
