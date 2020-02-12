
from nr.algo.graph.toposort import CyclicGraphError, toposort
import pytest


def test_toposort():
  nodes = {
    'a': [],
    'b': ['a'],
    'c': ['b'],
    'd': [],
    'e': ['d', 'b'],
    'f': ['c', 'e']
  }

  order = list(toposort(sorted(nodes), nodes.get))
  assert order == ['a', 'd', 'b', 'c', 'e', 'f']
  order = list(toposort(sorted(nodes, reverse=True), nodes.get))
  assert order == ['d', 'a', 'b', 'e', 'c', 'f']


def test_toposort_cycle():
  nodes = {
    'a': ['b'],
    'b': ['a']
  }
  with pytest.raises(CyclicGraphError):
    list(toposort(nodes, nodes.get))
