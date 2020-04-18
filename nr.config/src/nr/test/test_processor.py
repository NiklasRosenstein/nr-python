
from nr.config.processor import (parse_accessor_string, resolve_accessor_list, WILDCARD,
  Vars, process_config)


def test_parse_accessor_string():
  assert parse_accessor_string('a.b[0].c') == ['a', 'b', 0, 'c']
  assert parse_accessor_string('a[*].c') == ['a', WILDCARD, 'c']


def test_resolve_accessor_list():
  payload = {'a': {'b': [{'c': 1}, {'c': 42}, {'c': 50}]}}
  assert resolve_accessor_list(['a', 'b', 0, 'c'], payload) == 1
  assert resolve_accessor_list(['a', 'b', 1, 'c'], payload) == 42
  assert resolve_accessor_list(['a', 'b', WILDCARD, 'c'], payload) == [1, 42, 50]


def test_vars_processor():
  plugins = [Vars({'items': [{'value': 'foo'}, {'value': 'bar'}]})]
  payload = {'a': '{{items[0].value}}|{{items[1].value}}', 'b': '{{items[1].value}}', 'c': '{{items[*].value}}'}
  assert process_config(payload, plugins) == {'a': 'foo|bar', 'b': 'bar', 'c': ['foo', 'bar']}

  payload = {'a': '{{items[0]}}'}
  assert process_config(payload, plugins) == {'a': {'value': 'foo'}}

  payload = {'a': 'embedded in {{items[0]}} string'}
  assert process_config(payload, plugins) == {'a': 'embedded in {} string'.format(plugins[0]._data['items'][0])}
