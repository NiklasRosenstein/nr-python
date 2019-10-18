
import textwrap
import yaml

from nr.types.interface import implements
from nr.types.struct import JsonObjectMapper, Struct, Field, deserialize, serialize
from nr.types.struct.contrib.config import Preprocessor, preprocess, IConfigurable, load_configurable
from nr.types.utils import classdef


def test_preprocessor():
  p = Preprocessor({'$serviceRoot': '/opt/app'})

  assert p('{{$serviceRoot}}') == '/opt/app'

  assert p({'config': {'directories': {'data': '{{$serviceRoot}}/data'}}}) == \
    {'config': {'directories': {'data': '/opt/app/data'}}}


def test_preprocessor_flat_update():
  preprocessor = Preprocessor()

  preprocessor.flat_update({'directory': {'data': '/opt/app/data'}})
  assert preprocessor('{{directory.data}}') == '/opt/app/data'

  preprocessor.flat_update({'key': [{'value': 'foo'}]})
  print(preprocessor)
  assert preprocessor('{{key[0].value}}') == 'foo'


def test_preprocessor_e2e():
  yaml_code = textwrap.dedent('''
    config:
      directories:
        data: '{{$serviceRoot}}/data'
    runtime:
      media:
        path: '{{directories.data}}/media'
  ''')

  data = preprocess(
    yaml.safe_load(yaml_code),
    init_variables={'$serviceRoot': '/opt/app'}
  )

  assert data == {'runtime': {'media': {'path': '/opt/app/data/media'}}}


@implements(IConfigurable)
class ATestConfigurable(object):

  classdef.comparable(['config'])

  class Config(Struct):
    value = Field(int)

  def __init__(self, config):
    self.config = config

  @classmethod
  def get_configuration_model(cls):
    return cls.Config


def test_configurable():
  qualname = __name__ + ':' + 'ATestConfigurable'
  obj = load_configurable(qualname, {'value': 42})
  assert isinstance(obj, ATestConfigurable)
  assert obj.config.value == 42

  class Test(Struct):
    x = Field(IConfigurable)

  payload = {'x': {'class': qualname, 'value': 42}}
  obj = deserialize(JsonObjectMapper(), payload, Test)
  assert obj == Test(ATestConfigurable(ATestConfigurable.Config(42)))
  assert serialize(JsonObjectMapper(), obj, Test) == payload
