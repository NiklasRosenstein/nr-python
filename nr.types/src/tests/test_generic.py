
from nr.types import generic


def test_generic_param():

  class HashDict(generic.Generic['key_hash']):
    def __init__(self):
      generic.assert_initialized(self)
      self.data = {}
    def __getitem__(self, key):
      return self.data[self.key_hash(key)]
    def __setitem__(self, key, value):
      self.data[self.key_hash(key)] = value

  UnsafeHashDict = HashDict[hash]
  assert UnsafeHashDict.key_hash is hash
