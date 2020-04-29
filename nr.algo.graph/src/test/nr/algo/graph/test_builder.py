
import pytest
from nr.algo.graph.builder import Direction, DiGraph, BiGraph, NodeNotFound, EdgeNotFound


def init_graph(g, cycle=False):
    g.add_node(1, 'Foo')
    g.add_node(2, 'Bar')
    g.add_node(3, 'Baz')
    g.add_node(4, 'Faz')
    g.add_edge(1, 2)
    g.add_edge(1, 3)
    g.add_edge(2, 3)
    g.add_edge(4, 1)
    if cycle:
        g.add_edge(3, 4)


def _base_test(g):
    assert g.node_count() == 4
    assert set(g.nodes()) == set([1, 2, 3, 4])
    assert g.edge_count() == 4
    assert len(list(g.edges())) == 4
    assert g.node(1).data == 'Foo'
    assert g.node(2).data == 'Bar'
    assert g.node(3).data == 'Baz'
    assert g.node(4).data == 'Faz'
    with pytest.raises(NodeNotFound):
        g.node(5)
    assert g.edge(1, 2)
    assert g.edge(1, 3)
    assert g.edge(2, 3)
    assert g.edge(4, 1)
    with pytest.raises(EdgeNotFound):
        g.edge(4, 2)


def test_digraph():
    g = DiGraph()
    init_graph(g, cycle=False)
    _base_test(g)

    with pytest.raises(EdgeNotFound):
        g.edge(2, 1)
    with pytest.raises(EdgeNotFound):
        g.edge(3, 1)
    with pytest.raises(EdgeNotFound):
        g.edge(3, 2)
    with pytest.raises(EdgeNotFound):
        g.edge(1, 4)

    assert sorted(g.roots()) == [4]
    assert sorted(g.bases()) == [3]


def test_bigraph():
    g = BiGraph()
    init_graph(g, cycle=False)
    _base_test(g)

    assert g.edge(2, 1) is g.edge(1, 2)
    assert g.edge(3, 1) is g.edge(1, 3)
    assert g.edge(3, 2) is g.edge(2, 3)
    assert g.edge(4, 1) is g.edge(1, 4)

    assert list(g.roots()) == []
    assert list(g.bases()) == []
