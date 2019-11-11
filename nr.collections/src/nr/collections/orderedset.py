# -*- coding: utf8 -*-
# Copyright (c) 2019 Niklas Rosenstein
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

""" An implementation of an ordered set. """

from . import abc
import collections

__all__ = ['OrderedSet']


class OrderedSet(abc.MutableSet):

  def __init__(self, iterable=None):
    self._index_map = {}
    self._content = collections.deque()
    if iterable is not None:
      self |= iterable

  def __repr__(self):
    if not self._content:
      return '%s()' % (type(self).__name__,)
    return '%s(%r)' % (type(self).__name__, list(self))

  def __iter__(self):
    return iter(self._content)

  def __reversed__(self):
    return reversed(self._content)

  def __eq__(self, other):
    if type(other) is OrderedSet:
      return len(self) == len(other) and list(self) == list(other)
    return False

  def __ne__(self, other):
    if type(other) is OrderedSet:
      return len(self) != len(other) or list(self) != list(other)
    return False

  def __len__(self):
    return len(self._content)

  def __contains__(self, key):
    return key in self._index_map

  def __getitem__(self, index):
    return self._content[index]

  def __le__(self, other):
      return all(e in other for e in self)

  def __lt__(self, other):
      return self <= other and self != other

  def __ge__(self, other):
      return all(e in self for e in other)

  def __gt__(self, other):
      return self >= other and self != other

  def add(self, key):
    if key not in self._index_map:
      self._index_map[key] = len(self._content)
      self._content.append(key)

  def copy(self):
    return type(self)(self)

  def discard(self, key):
    if key in self._index_map:
      index = self._index_map.pop(key)
      del self._content[index]

  def pop(self, last=True):
    if not self._content:
      raise KeyError('set is empty')
    key = self._content.pop() if last else self._content.popleft()
    self._index_map.pop(key)
    return key

  def update(self, iterable):
    for x in iterable:
      self.add(x)
