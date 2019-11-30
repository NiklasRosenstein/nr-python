
from nr.databind.core import Location, Path, IntegerType
import pytest


def _mkloc(path, value=None, datatype=None):
  return Location(value, datatype, Path(path), None)


def test_location_str_empty():
  assert str(_mkloc([]).path) == '$'


def test_location_str_simple():
  assert str(_mkloc(['foobar']).path) == '$.foobar'
  assert str(_mkloc(['spam', 'baz']).path) == '$.spam.baz'
  assert str(_mkloc([0, 1, 5]).path) == '$[0][1][5]'


def test_location_str_mixed():
  assert str(_mkloc(['foobar', 3, 'type']).path) == '$.foobar[3].type'


def test_location_str_escape():
  assert str(_mkloc(['root', 1, 'needs:escaping']).path) == '$.root[1]."needs:escaping"'
  assert str(_mkloc(['"also needs escaping']).path) == '$."\\"also needs escaping"'
  assert str(_mkloc(['no-escaping']).path) == '$.no-escaping'


def test_location_resolve():
  data = {'2.4.0': {'foo': {'bar': {'spam-egg': []}}}}

  location = _mkloc(['2.4.0', 'foo', 'bar', 'spam-egg'])
  assert location.path.resolve(data) == []

  location = _mkloc(['2.4.0', 'foo', 'bar', 'spam-eggzzz'])
  with pytest.raises(KeyError) as excinfo:
    location.path.resolve(data)
  assert str(excinfo.value) == repr(str(location.path))

  location = _mkloc(['2.4.0', 'foo', 'bar', 'spam-egg', 1])
  with pytest.raises(IndexError) as excinfo:
    location.path.resolve(data)
  assert str(excinfo.value) == 'list index out of range at $."2.4.0".foo.bar.spam-egg[1]'


def test_location_resolve_and_emplace():
  proxy = _mkloc(['foo', 1, 'bar'])
  assert str(proxy.path) == '$.foo[1].bar'

  data = {'foo': [{'bar': 11}]}
  with pytest.raises(IndexError) as exc:
    proxy.path.resolve(data)

  data = {'foo': [{'bar': 11}, {'bar': 42}]}
  assert proxy.path.resolve(data) == 42
