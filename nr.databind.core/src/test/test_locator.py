
from nr.databind.core import Locator, IntegerType
import pytest


def test_location_str_empty():
  assert str(Locator([])) == '$'


def test_location_str_simple():
  assert str(Locator(['foobar'])) == '$.foobar'
  assert str(Locator(['spam', 'baz'])) == '$.spam.baz'
  assert str(Locator([0, 1, 5])) == '$[0][1][5]'


def test_location_str_mixed():
  assert str(Locator(['foobar', 3, 'type'])) == '$.foobar[3].type'


def test_location_str_escape():
  assert str(Locator(['root', 1, 'needs:escaping'])) == '$.root[1]."needs:escaping"'
  assert str(Locator(['"also needs escaping'])) == '$."\\"also needs escaping"'
  assert str(Locator(['no-escaping'])) == '$.no-escaping'


def test_location_resolve():
  data = {'2.4.0': {'foo': {'bar': {'spam-egg': []}}}}

  location = Locator(['2.4.0', 'foo', 'bar', 'spam-egg'])
  assert location.access(data) == []

  location = Locator(['2.4.0', 'foo', 'bar', 'spam-eggzzz'])
  with pytest.raises(KeyError) as excinfo:
    location.access(data)
  assert str(excinfo.value) == repr(str(location))

  location = Locator(['2.4.0', 'foo', 'bar', 'spam-egg', 1])
  with pytest.raises(IndexError) as excinfo:
    location.access(data)
  assert str(excinfo.value) == 'list index out of range at $."2.4.0".foo.bar.spam-egg[1]'


def test_location_resolve_and_emplace():
  proxy = Locator(['foo', 1, 'bar'])
  assert str(proxy) == '$.foo[1].bar'

  data = {'foo': [{'bar': 11}]}
  with pytest.raises(IndexError) as exc:
    proxy.access(data)

  data = {'foo': [{'bar': 11}, {'bar': 42}]}
  assert proxy.access(data) == 42
