
from nr.algo.graph import LambdaDiGraph
from nr.algo.graph.builder import DiGraph, BiGraph
from nr.algo.graph.toposort import CyclicGraphError, toposort
from test_builder import init_graph
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

  order = list(toposort(LambdaDiGraph(sorted(nodes), nodes.get)))
  assert order == ['a', 'd', 'b', 'c', 'e', 'f']
  order = list(toposort(LambdaDiGraph(sorted(nodes, reverse=True), nodes.get)))
  assert order == ['d', 'a', 'b', 'e', 'c', 'f']


def test_toposort_cycle():
  nodes = {
    'a': ['b'],
    'b': ['a']
  }
  with pytest.raises(CyclicGraphError):
    list(toposort(LambdaDiGraph(nodes, nodes.get)))


def test_toposort_digraph():
  g = DiGraph()
  init_graph(g)
  order = list(toposort(g))
  assert order == [4, 1, 2, 3]
