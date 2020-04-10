
from nr.collections import generic
import pytest


def test_generic_param():

  class HashDict(generic.Generic):
    def __generic_init__(cls, key_hash):
      cls.key_hash = key_hash
    def __init__(self):
      assert not self.__is_generic__
      self.data = {}
    def __getitem__(self, key):
      return self.data[self.key_hash(key)]
    def __setitem__(self, key, value):
      self.data[self.key_hash(key)] = value
    def __repr__(self):
      return repr(self.data)

  UnsafeHashDict = HashDict[hash]
  assert UnsafeHashDict.key_hash is hash

  class HashWith(object):
    def __init__(self, v):
      self.v = v
    def __hash__(self):
      return hash(self.v)

  d = UnsafeHashDict()
  a, b = HashWith(3), HashWith(3)
  assert a is not b
  d[a] = 42
  assert d[b] == 42

  with pytest.raises(AssertionError):
    HashDict()
