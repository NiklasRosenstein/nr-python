
from nr.interface import implements
from nr.databind.contrib.preprocessor import *
from nr.pylang.utils import classdef
from ..fixtures import mapper
import textwrap
import yaml


def test_preprocessor():
  p = Preprocessor([Vars({'$serviceRoot': '/opt/app'})])
  assert p('{{$serviceRoot}}') == '/opt/app'
  assert p({'config': {'directories': {'data': '{{$serviceRoot}}/data'}}}) == \
    {'config': {'directories': {'data': '/opt/app/data'}}}


def test_preprocessor_flat_update():
  vars_plugin = Vars()
  vars_plugin.flat_update({'directory': {'data': '/opt/app/data'}})

  preprocessor = Preprocessor([vars_plugin])
  assert preprocessor('{{directory.data}}') == '/opt/app/data'

  vars_plugin.flat_update({'key': [{'value': 'foo'}]})
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

  data = yaml.safe_load(yaml_code)
  runtime = config_preprocess(data['config'], data['runtime'], [
    Vars({'$serviceRoot': '/opt/app'})
  ])

  assert runtime == {'media': {'path': '/opt/app/data/media'}}
