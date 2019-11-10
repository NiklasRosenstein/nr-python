
from nr.types.collections import ChainDict, ObjectFromDict, OrderedSet


def test_ChainDict():
  a = {'foo': 42}
  b = {'bar': 'spam'}
  c = {}
  d = ChainDict({}, a, b, c)

  assert str(d) == 'ChainDict({})'.format({'foo': 42, 'bar': 'spam'})
  assert d['foo'] == a['foo']
  assert d['bar'] == b['bar']
  assert sorted(d.keys()) == ['bar', 'foo']

  d['hello'] = 'World'
  assert a == {'foo': 42}
  assert b == {'bar': 'spam'}
  assert c == {}
  assert d == {'foo': 42, 'bar': 'spam', 'hello': 'World'}

  del d['foo']
  assert a == {'foo': 42}
  assert b == {'bar': 'spam'}
  assert c == {}
  assert d == {'bar': 'spam', 'hello': 'World'}

  d['foo'] = 99
  assert a == {'foo': 42}
  assert b == {'bar': 'spam'}
  assert c == {}
  assert d == {'foo': 99, 'bar': 'spam', 'hello': 'World'}

  d.clear()
  assert a == {'foo': 42}
  assert b == {'bar': 'spam'}
  assert c == {}
  assert d == {}


def test_ObjectFromDictping():
  d = ChainDict({'a': 42, 'b': 'foo'}, {'c': 'egg'})
  o = ObjectFromDict(d)
  assert o.a == 42
  assert o.b == 'foo'
  assert o.c == 'egg'
  assert dir(o), ['a', 'b', 'c']


def test_OrderedSet():
  s1 = OrderedSet('abcd')
  s2 = OrderedSet('cdef')
  assert ''.join(s1) == 'abcd'
  assert ''.join(s2) == 'cdef'
  assert s1 != s2
  assert (s1 - s2) == OrderedSet('ab')
  assert (s2 - s1) == OrderedSet('ef')
  assert (s1 | s2) == OrderedSet('abcdef')
  assert OrderedSet(reversed(s1)) == OrderedSet('dcba')
