
import textwrap
import yaml

from nr.interface import implements
from nr.databind import JsonObjectMapper, Struct, Field, deserialize, serialize
from nr.databind.contrib.preprocessor import Preprocessor, preprocess
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
