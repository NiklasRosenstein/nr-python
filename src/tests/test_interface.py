
import pytest

from nr.types.interface import *


def test_constructed():

  class Constructed(Exception):
    pass

  class IFoo(Interface):
    x = attr()
    def __constructed__(self):
      raise Constructed()

  @implements(IFoo)
  class Foo(object):
    def __init__(self, x=None):
      super(Foo, self).__init__()
      self.x = x

  with pytest.raises(Constructed):
    Foo()


def test_value():

  class IFoo(Interface):
    x = attr()

  @implements(IFoo)
  class Foo(object):
    def __init__(self, x=None):
      super(Foo, self).__init__()
      self.x = x

  assert Foo().x is None
  assert Foo('foobar!').x == 'foobar!'


def test_final():

  class IFoo(Interface):
    @final
    def bar(self):
      return 'Bar!'

  @implements(IFoo)
  class Foo(object):
    pass

  assert Foo().bar() == 'Bar!'

  with pytest.raises(ImplementationError):
    @implements(IFoo)
    class Foo(object):
      def bar(self):
        return 'Hello!'


def test_override():

  class IFoo(Interface):
    def bar(self):
      pass

  @implements(IFoo)
  class Foo(object):
    @override
    def bar(self):
      return 42

  with pytest.raises(ImplementationError) as excinfo:
    @implements(IFoo)
    class Foo(object):
      @override
      def bar(self):
        return 42
      @override
      def bars(self):
        return 42
  assert excinfo.value.interfaces == []
  assert excinfo.value.errors == ["'bars' does not override a method of any of the implemented interfaces."]

  with pytest.raises(ImplementationError) as excinfo:
    @implements(IFoo)
    class Foo(object):
      @override
      def bars(self):
        return 42
  assert excinfo.value.interfaces == [IFoo]
  assert excinfo.value.errors == [
    "'bars' does not override a method of any of the implemented interfaces.",
    "missing method: bar()"
  ]


def test_interface_constructor():

  class IFoo(Interface):
    def __init__(self):
      self.x = {}

  class IBar(Interface):
    def __init__(self):
      self.y = {}

  @implements(IFoo, IBar)
  class Foo(object):
    def __init__(self, value):
      super(Foo, self).__init__()
      assert hasattr(self, 'x')
      assert hasattr(self, 'y')
      self.x['value'] = value
      self.y['value'] = value * 2

  assert Foo(42).x['value'] == 42
  assert Foo(42).y['value'] == 84


def test_default():

  class IFoo(Interface):
    @default
    def __eq__(self, other):
      return other == '42'

  class ISubClass(IFoo):
    @default
    def bar(self):
      return 'Bar!'

  @implements(ISubClass)
  class Foo(object):
    pass

  @implements(ISubClass)
  class Bar(object):
    @override
    def __eq__(self, other):
      return other == '52'
    @override
    def bar(self):
      return 'Foo!'

  assert Foo().bar() == 'Bar!'
  assert Bar().bar() == 'Foo!'
  assert Foo() == '42'
  assert Bar() == '52'


def test_staticmethod_override():

  class IFoo(Interface):
    @staticmethod
    def a_static_method():
      pass

  assert 'a_static_method' in IFoo
  assert IFoo['a_static_method'].static

  class IBar(Interface):
    @classmethod
    def a_class_method():
      pass

  assert 'a_class_method' in IBar
  assert IBar['a_class_method'].static  # A classmethod is also considered static

  # TODO(nrosenstein): Assert that overriding a static method non-statically
  #                    does not work.


def test_attr_default():

  class IFoo(Interface):
    x = attr(int, 24)

  @implements(IFoo)
  class Bar(object):
    pass

  assert not hasattr(Bar, 'x')
  assert hasattr(Bar(), 'x')
  assert Bar().x == 24


def test_staticattr_default():

  class IFoo(Interface):
    x = staticattr(24)

  @implements(IFoo)
  class Bar(object):
    pass

  assert hasattr(Bar, 'x')
  assert Bar.x == 24
  assert Bar().x == 24
  assert 'x' not in vars(Bar())


def test_override_works_on_staticmethod():
  """
  In Python 2.7 you cannot set a member on an instance of the [[staticmethod]]
  class. This means a previous implementation of [[override]] resulted in an
  [[AttributeError]].
  """

  class IFoo(Interface):
    @staticmethod
    def a_static_method():
      pass

  @implements(IFoo)
  class Bar(object):
    @override
    @staticmethod
    def a_static_method():
      pass


def test_property_missing():

  class IFoo(Interface):
    @property
    def foo(self):
      pass

  with pytest.raises(ImplementationError) as excinfo:
    @implements(IFoo)
    class Bar(object):
      pass
  assert excinfo.value.interfaces == [IFoo]
  assert excinfo.value.errors == ["missing property: foo"]


def test_property_wrongtype():

  class IFoo(Interface):
    @property
    def foo(self):
      pass

  with pytest.raises(ImplementationError) as excinfo:
    @implements(IFoo)
    class Bar(object):
      def foo(self):
        pass
  assert excinfo.value.interfaces == [IFoo]
  assert excinfo.value.errors == ["expected property, got instancemethod: foo"]


def test_property_ok():

  class IFoo(Interface):
    @property
    def foo(self):
      pass

  @implements(IFoo)
  class Bar(object):
    @property
    def foo(self):
      pass

    # This works because this is not necessarily a semantic that is
    # incompatible with the interface.
    @foo.setter
    def foo(self, value):
      pass


def test_property_missing_setter():

  class IFoo(Interface):
    @property
    def foo(self):
      pass

    @foo.setter
    def foo(self, value):
      pass

  with pytest.raises(ImplementationError) as excinfo:
    @implements(IFoo)
    class Bar(object):
      @property
      def foo(self):
        pass
  assert excinfo.value.interfaces == [IFoo]
  assert excinfo.value.errors == ["property foo: missing setter"]


def test_property_final():

  class AError(Exception):
    pass

  class BError(Exception):
    pass

  class IFoo(Interface):
    @property
    def foo(self):
      pass

    @foo.setter
    @final
    def foo(self, value):
      raise AError

  @implements(IFoo)
  class Bar(object):
    @property
    def foo(self):
      raise BError

  with pytest.raises(AError):
    Bar().foo = 42

  with pytest.raises(BError):
    Bar().foo

  with pytest.raises(ImplementationError) as excinfo:
    @implements(IFoo)
    class Bar(object):
      @property
      def foo(self):
        pass

      @foo.setter
      def foo(self, value):
        pass
  assert excinfo.value.interfaces == [IFoo]
  assert excinfo.value.errors == ["property foo: setter must not be implemented"]


def test_property_wrong_decoration():

  # TODO(nrosenstein): This should actually raise an error

  class IFoo(Interface):
    @property
    def foo(self):
      pass

    @final
    @foo.setter
    def foo(self, value):
      raise AError

  assert 'foo' not in IFoo
