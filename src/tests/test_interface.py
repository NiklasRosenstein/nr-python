
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

  with pytest.raises(ImplementationError):
    @implements(IFoo)
    class Foo(object):
      @override
      def bars(self):
        return 42


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


class test_staticmethod_override():

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


class test_attr_default():

  class IFoo(Interface):
    x = attr(int, 24)

  @implements(IFoo)
  class Bar(object):
    pass

  assert not hasattr(Bar, 'x')
  assert hasattr(Bar(), 'x')
  assert Bar().x == 24


class test_staticattr_default():

  class IFoo(Interface):
    x = staticattr(24)

  @implements(IFoo)
  class Bar(object):
    pass

  assert hasattr(Bar, 'x')
  assert Bar.x == 24
  assert Bar().x == 24
  assert 'x' not in vars(Bar())
