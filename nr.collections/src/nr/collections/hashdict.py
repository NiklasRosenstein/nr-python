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

from . import abc, generic
from nr.metaclass.deconflict import deconflicted_base


class HashDict(deconflicted_base(generic.Generic, abc.MutableMapping)):
  """
  This dictionary type can be specialized by specifying a hash function,
  allowing it to be used even with unhashable types as keys.

  Example 1: Specialization through subclassing

  ```python
  class MyDict(HashDict):
    def key_hash(self, key):
      return ...
  ```

  Example 2: Explicit type specialization

  ```
  def my_key_hash(x):
    return ...
  MyDict = HashDict[my_key_hash]
  ```
  ```
  """

  class KeyWrapper(object):
    def __init__(self, key, hash_func):
      self.key = key
      self.hash_func = hash_func
    def __repr__(self):
      return repr(self.key)
    def __hash__(self):
      return self.hash_func(self.key)
    def __eq__(self, other):
      return self.key == other.key
    def __ne__(self, other):
      return self.key != other.key

  def __generic_init__(cls, key_hash):
    cls.key_hash = staticmethod(key_hash)

  def __init__(self):
    assert not self.__is_generic__
    self._dict = {}

  def __repr__(self):
    return repr(self._dict)

  def __len__(self):
    return len(self._dict)

  def __getitem__(self, key):
    key = self.KeyWrapper(key, self.key_hash)
    return self._dict[key]

  def __setitem__(self, key, value):
    key = self.KeyWrapper(key, self.key_hash)
    self._dict[key] = value

  def __delitem__(self, key):
    key = self.KeyWrapper(key, self.key_hash)
    del self._dict[key]

  def __iter__(self):
    return self.iterkeys()

  def __contains__(self, key):
    return self.KeyWrapper(key, self.key_hash) in self._dict

  def items(self):
    return list(self.iteritems())

  def keys(self):
    return list(self.iterkeys())

  def values(self):
    return self._dict.values()

  def iteritems(self):
    for key, value in self._dict.iteritems():
      yield key.key, value

  def iterkeys(self):
    for key in self._dict.keys():
      yield key.key

  def itervalues(self):
    return self._dict.itervalues()

  def get(self, key, *args):
    key = self.KeyWrapper(key, self.key_hash)
    return self._dict.get(key, *args)

  def setdefault(self, key, value):
    key = self.KeyWrapper(key, self.key_hash)
    return self._dict.setdefault(key, value)
