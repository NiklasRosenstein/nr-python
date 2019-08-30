
from nr.types.collections._ordereddict import OrderedDict


def test_order():
  d = OrderedDict([('a', 10), ('b', 24), ('c', 5)])
  assert list(d.keys()) == ['a', 'b', 'c']
  assert list(d.values()) == [10, 24, 5]
