
from nr.refreshable import Refreshable


def test_refreshable():
  root = Refreshable(10)
  child = root.map(lambda n: n * 10)

  assert root.get() == 10
  assert child.get() == 100

  root.update(42)
  assert root.get() == 42
  assert child.get() == 420
