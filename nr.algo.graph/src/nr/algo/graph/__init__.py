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

import nr.interface

__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
__version__ = '0.1.2'


class IGraph(nr.interface.Interface):
  """
  Interface for (bi-) directed graphs.
  """

  def is_directed(self):  # type: () -> bool
    pass

  def node_count(self):  # type: () -> int
    pass

  def nodes(self):  # type: () -> Iterable[Any]
    pass

  def edge_count(self):  # type: () -> int
    pass

  def inbound_connections(self, node):  # type: (Any) -> Sequence[Any]
    pass

  def outbound_connections(self, node):  # type: (Any) -> Sequence[Any]
    pass

  @nr.interface.default
  def roots(graph):  # type: () -> Iterable[Any]
    """
    Iterate over the root nodes of a graph (those that have no inbound connections).
    """

    for node in graph.nodes():
      if not graph.inbound_connections(node):
        yield node

  @nr.interface.default
  def bases(graph):  # type: () -> Iterable[Any]
    """
    Iterates over the base nodes of a graph (those that have no outbound connections).
    """

    for node in graph.nodes():
      if not graph.outbound_connections(node):
        yield node


@nr.interface.implements(IGraph)
class LambdaDiGraph(object):

  def __init__(self, nodes, get_inbounds, get_outbounds=None):
    # type: (Sequence[Any], Callable[Sequence[Any], [Any]], Optional[Callable[Sequence[Any], [Any]]]) -> None
    if get_outbounds is None:
      _dependents = {}
      for node in nodes:
        for dependent in get_inbounds(node):
          _dependents.setdefault(dependent, []).append(node)
      def get_outbounds(node):
        return _dependents.get(node, [])

    self._nodes = nodes
    self._edge_count = None
    self.inbound_connections = get_inbounds
    self.outbound_connections = get_outbounds

  def is_directed(self):
    return True

  def node_count(self):
    return len(self._nodes)

  def nodes(self):
    return iter(self._nodes)

  def edge_count(self):
    if self._edge_count is None:
      self._edge_count = 0
      for node in self._nodes:
        self._edge_count += len(self.inbound_connections(node))
    return self._edge_count

  def inbound_connections(self, node):
    # Will be overwritten by the constructor.
    raise NotImplementedError

  def outbound_connections(self, node):
    # Will be overwritten by the constructor.
    raise NotImplementedError
