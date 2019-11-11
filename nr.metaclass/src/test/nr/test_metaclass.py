
from nr.metaclass.inline import InlineMetaclassBase
from nr.metaclass.deconflict import get_conflicting_metaclasses


def test_InlineMetaclassBase():

  class MyClass(InlineMetaclassBase):
    def __metainit__(self, name, bases, attr):
      self.value = 'foo'

  assert MyClass.value == 'foo'


def test_get_conflicting_metaclasses():
  class A(type):
    pass
  class B(type):
    pass
  class C(B):
    pass

  assert get_conflicting_metaclasses((A,)) == []
  assert get_conflicting_metaclasses((A, type)) == []
  assert get_conflicting_metaclasses((A, B)) == [A, B]
  assert get_conflicting_metaclasses((A, C)) == [A, C]
  assert get_conflicting_metaclasses((B, C)) == []
