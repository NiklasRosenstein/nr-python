
from nr.collections.hashdict import HashDict


def test_hash_dict():

  m = HashDict[hash]()
  m['foo'] = 42
  m['foo'] = 99
  m['foo'] = 102

  assert len(m) == 1
  assert sorted(m.keys()) == ['foo']
  assert sorted(m.values()) == [102]

  def increment(x, _c={}):
    _c['x'] = _c.get('x', -1) + 1
    return _c['x']

  m = HashDict[increment]()
  m['foo'] = 42
  m['foo'] = 99
  m['foo'] = 102

  assert len(m) == 3
  assert sorted(m.keys()) == ['foo', 'foo', 'foo']
  assert sorted(m.values()) == [42, 99, 102]
