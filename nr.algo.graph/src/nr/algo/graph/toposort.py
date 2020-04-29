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


class CyclicGraphError(Exception):
  pass


def toposort(graph):  # type: (IGraph) -> Iterable[Any]
  """
  Performs topological sorting on the *graph* object, returning the nodes in topological order.
  The algorithm performs stable sorting, meaning that it retains the original order of nodes
  returned by #IGraph.nodes() where possible.
  """

  assert graph.is_directed(), "toposort() works only with directed graphs"

  num_edges = graph.edge_count()
  visit = list(graph.roots())

  seen = set()
  while visit:
    node = visit.pop(0)
    yield node
    for dependent in graph.outbound_connections(node):
      seen.add((node, dependent))
      if all((x, dependent) in seen for x in graph.inbound_connections(dependent)):
        visit.append(dependent)

  if len(seen) != num_edges:
    raise CyclicGraphError(len(seen), num_edges)
