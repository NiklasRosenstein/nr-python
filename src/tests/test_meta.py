
from nr.types.meta import InlineMetaclassBase

def test_InlineMetaclassBase():

  class MyClass(InlineMetaclassBase):
    def __metainit__(self, name, bases, attr):
      self.value = 'foo'

  assert MyClass.value == 'foo'
