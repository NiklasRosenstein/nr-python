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

class CyclicGraphError(Exception):
  pass


def toposort(nodes, get_dependencies, get_dependents=None):
  # type: (List[Any], Callable[List[Any], [Any]]) -> Iterable[Any]
  """
  Performs topological sorting to the specified set of *nodes* and returns
  a generator yielding the values of *nodes* in sorted order. If the dependents
  of a node are know, *get_dependents* can be specified, otherwise it is built
  by reversing *get_dependencies*.

  Notes:

  * No element in *nodes* must be duplicate.
  """

  if get_dependents is None:
    _dependents = {}
    for node in nodes:
      for dependent in get_dependencies(node):
        _dependents.setdefault(dependent, []).append(node)
    def get_dependents(node):
      return _dependents.get(node, [])

  visit = []
  num_edges = 0
  for node in nodes:
    deps = get_dependencies(node)
    num_edges += len(deps)
    if not deps:
      visit.append(node)

  seen = set()
  while visit:
    node = visit.pop(0)
    yield node
    for dependent in get_dependents(node):
      seen.add((node, dependent))
      if all((x, dependent) in seen for x in get_dependencies(dependent)):
        visit.append(dependent)

  if len(seen) != num_edges:
    raise CyclicGraphError(len(seen), num_edges)
