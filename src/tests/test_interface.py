
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
    def bar(self):
      return 'Bar!'

  @implements(IFoo)
  class Foo(object):
    pass

  @implements(IFoo)
  class Bar(object):
    def bar(self):
      return 'Foo!'

  assert Foo().bar() == 'Bar!'
  assert Bar().bar() == 'Foo!'
