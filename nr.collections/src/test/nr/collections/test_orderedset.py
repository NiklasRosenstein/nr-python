
from nr.collections.orderedset import OrderedSet


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
