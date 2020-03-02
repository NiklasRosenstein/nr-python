
from nr.metaclass.inline import InlineMetaclassBase
from nr.metaclass.deconflict import deconflict_bases, get_conflicting_metaclasses, reduce_mro
import pytest


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


def test_reduce_mro():
  class D(InlineMetaclassBase):
    pass

  with pytest.raises(TypeError) as excinfo:
    type('Test', (object, D), {})
  assert 'consistent method resolution' in str(excinfo.value)

  type('Test', reduce_mro(object, D), {})

  assert reduce_mro(object, D) == (D,)


def test_deconflict_bases(*bases):
  class A(InlineMetaclassBase):
    pass

  class B(A):
    pass

  print(deconflict_bases(object, B))
  e
