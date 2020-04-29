# -*- coding: utf8 -*-
# The MIT License (MIT)
#
# Copyright (c) 2020 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from .. import IGraph
from .builder import Graph as DotvizGraph, Writer as DotvizWriter
# from typing import TextIO


def dotviz(graph):  # type: (IGraph) -> str
  pass

def dotviz(graph, fp):  # type: (IGraph, TextIO) -> None
  pass

def dotviz(graph, fp=None):
  """
  Fast dotviz for #IGraph implementations.
  """

  viz = DotvizGraph(graph.is_directed())
  for node_id in graph.nodes():
    viz.node(node_id)
    for other_node_id in graph.inbound_connections(node_id):
      viz.edge(node_id, other_node_id)
  return viz.render(fp)
