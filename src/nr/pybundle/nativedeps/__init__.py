# Copyright (c) 2018 Niklas Rosenstein
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
"""
This is a cross-platform module to allow finding dependencies of shared
libraries and executables.
"""

import os
import sys
from ._base import Dependency
from ..utils import system


if system.is_win:
  from .windll import get_dependencies, resolve_dependency
else:
  raise NotImplemntedError(sys.platform)


class Collection(object):
  """
  Represents a collection of native dependencies. A useful data structure
  when recursively collecting dependencies of one or multiple binaries.
  """

  def __init__(self, exclude_system_deps=False):
    self.cache = {}  # lower-case filename -> get_dependencies() result
    self.deps = {}  # lower-case filename -> Dependency
    self.search_path = os.environ['PATH'].split(os.pathsep)
    self.recursively_visited = set()
    self.exclude_system_deps = exclude_system_deps

  def __iter__(self):
    return iter(self.deps.values())

  def add(self, filename, dependencies_only=False, recursive=False):
    """
    Add *filename* as a binary and its resolved dependencies to the
    collection. If *dependencies_only* is #True, the *filename* itself
    will not be added to the collection.

    *filename* may also be a #Dependency object.
    """

    if isinstance(filename, Dependency):
      dep = filename
      dep.filename = resolve_dependency(dep, self.search_path)
    else:
      dep = Dependency(os.path.basename(filename), filename)
    if not dependencies_only:
      dep = self.deps.setdefault(dep.name.lower(), dep)

    if not dep.filename:
      return

    try:
      dependencies = self.cache[dep.name.lower()]
    except KeyError:
      dependencies = get_dependencies(dep.filename, self.exclude_system_deps)
      self.cache[dep.name.lower()] = dependencies

    if dep.name.lower() in self.recursively_visited:
      return
    if recursive:
      self.recursively_visited.add(dep.name.lower())

    for other_dep in dependencies:
      other_dep = self.deps.setdefault(other_dep.name.lower(), other_dep)
      resolve_dependency(other_dep, self.search_path)
      if recursive and other_dep.filename:
        self.add(other_dep.filename, recursive=True)

    return dep
