# -*- coding: utf8 -*-
# The MIT License (MIT)
#
# Copyright (c) 2020 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

from . import IGraph
import collections
import nr.interface
import six

Node = collections.namedtuple('Node', 'id,data')
Edge = collections.namedtuple('Edge', 'a,b,data')


class GraphError(Exception):
  pass


class NodeError(GraphError):
  def __init__(self, node_id):
    self.node_id = node_id
  def __str__(self):
    return str(self.node_id)


class NodeNotFound(NodeError):
  pass


class NodeAlreadyExists(NodeError):
  pass


class EdgeError(GraphError):
  def __init__(self, node_a, node_b):
    self.node_a = node_a
    self.node_b = node_b
  def __str__(self):
    return '{!r} - {!r}'.format(self.node_a, self.node_b)


class EdgeNotFound(EdgeError):
  pass


class EdgeAlreadyExists(EdgeError):
  pass


class DiGraph(object):

  def __init__(self):  # type: (bool) -> None
    self._nodes = {}
    self._edges = {}
    self._edges_reverse = {}

  def is_directed(self):  # type: () -> bool
    return True

  def node_count(self):  # type: () -> int
    return len(self._nodes)

  def edge_count(self):  # type: () -> int
    return sum(len(x) for x in six.itervalues(self._edges))

  def node(self, node_id):  # type: (Any) -> Node
    try:
      return self._nodes[node_id]
    except KeyError:
      raise NodeNotFound(node_id)

  def nodes(self):  # type: () -> Iterable[Node]
    return iter(self._nodes.values())

  def add_node(self, node_id, data=None, exist_ok=False):  # type: (Any, Any) -> Node
    if node_id in self._nodes:
      if exist_ok:
        return self._nodes[node_id]
      raise NodeAlreadyExists(node_id)
    node = self._nodes[node_id] = Node(node_id, data)
    return node

  def edge(self, node_a, node_b):  # type: (Any, Any) -> Edge
    if node_a not in self._nodes:
      raise NodeNotFound(node_a)
    if node_b not in self._nodes:
      raise NodeNotFound(node_b)
    connections = self._edges.get(node_a)
    if connections is None:
      raise EdgeNotFound(node_a, node_b)
    edge = connections.get(node_b)
    if edge is None:
      raise EdgeNotFound(node_a, node_b)
    return edge

  def edges(self, node_id=None, reverse=False):  # type: (Optional[Any], bool) -> Iterable[Edge]
    target = self._edges_reverse if reverse else self._edges
    if node_id is not None:
      if node_id not in self._nodes:
        raise NodeNotFound(node_id)
      for _ in six.itervalues(target.get(node_id, {})):
        yield _
    else:
      for connections in six.itervalues(target):
        for _ in six.itervalues(connections):
          yield _

  def add_edge(self, node_a, node_b, data=None, exist_ok=False):  # type: (Any, Any, Any) -> Edge
    if node_a not in self._nodes:
      raise NodeNotFound(node_a)
    if node_b not in self._nodes:
      raise NodeNotFound(node_b)
    connections = self._edges.setdefault(node_a, {})
    if node_b in connections:
      if exist_ok:
        return connections[node_b]
      raise EdgeAlreadyExists(node_a, node_b)
    edge = connections[node_b] = Edge(node_a, node_b, data)
    self._edges_reverse.setdefault(node_b, {})[node_a] = edge
    return edge

  def adapter(self):  # type: () -> IGraph
    return GraphAdapter(self)


class BiGraph(DiGraph):

  def is_directed(self):
    return False

  def edge(self, node_a, node_b):
    node_a, node_b = sorted((node_a, node_b))
    return super(BiGraph, self).edge(node_a, node_b)

  def edges(self, node_id=None, reverse=False):
    # Ignoring the "reverse" argument intentionally.
    for _ in super(BiGraph, self).edges(node_id):
      yield _
    if node_id is not None:
      connections = self._edges_reverse.get(node_id, {})
      for _ in six.itervalues(connections):
        yield _

  def add_edge(self, node_a, node_b, data=None):
    node_a, node_b = sorted((node_a, node_b))
    return super(BiGraph, self).add_edge(node_a, node_b, data)


@nr.interface.implements(IGraph)
class GraphAdapter(object):

  def __init__(self, graph):  # type: (DiGraph) -> None
    self._graph = graph

  def node_count(self):
    return self._graph.node_count()

  def nodes(self):
    return (n.id for n in self._graph.nodes())

  def is_directed(self):
    return self._graph.is_directed()

  def inbound_connections(self, node_id):
    return [x.b for x in self._graph.edges(node_id)]

  def outbound_connections(self, node_id):
    return [x.a for x in self._graph.edges(node_id, reverse=True)]
