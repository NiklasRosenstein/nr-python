
import pytest
import six
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


def test_interface_cannot_be_constructed():
  class IFoo(Interface):
    def bar(self):
      pass
  with pytest.raises(RuntimeError) as excinfo:
    IFoo()
  assert str(excinfo.value) == 'interface IFoo cannot be instantiated'


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


def test_attr_overridden_at_classlevel():

  class IFoo(Interface):
    x = attr()

  @implements(IFoo)
  class Foo(object):
    x = 42

  assert hasattr(Foo, 'x')
  assert Foo.x == 42
  assert Foo().x == 42

  class ISubclassFoo(IFoo):
    x = 'foobar'

  # Interface members are removed from the interface class itself
  # because they are moved into the members dict.
  # "x" is a member inherited from the parent interface.
  assert not hasattr(ISubclassFoo, 'x')


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


def test_implementation_subclassing():

  class I(Interface):
    def a(self): pass

  @implements(I)
  class A(object):
    @override
    def a(self): return 42

  assert A.__implements__ == [I]
  assert A().a() == 42

  class B(A):
    @override
    def a(self): return 99

  assert B.__implements__ == [I]
  assert B().a() == 99


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


def test_default_classmethod():

  class IFoo(Interface):
    @default
    @classmethod
    def my_classmethod(self):
      return self.__name__

  @implements(IFoo)
  class NoOverride(object):
    pass

  assert NoOverride.my_classmethod() == 'NoOverride'

  @implements(IFoo)
  class WithOverride(object):
    @classmethod
    def my_classmethod(self):
      return 'Foobar!'

  assert WithOverride.my_classmethod() == 'Foobar!'


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

  class IFoo(Interface):
    x = attr(default=None)

  @implements(IFoo)
  class Impl(object):
    pass

  assert not hasattr(Impl, 'x')
  assert hasattr(Impl(), 'x')
  assert Impl().x is None


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


def test_staticattr_for_classmethod():

  class IFoo(Interface):
    A = '-abc'

    @staticattr
    @classmethod
    def test(cls):
      return cls.__name__ + cls.A

  class IBar(IFoo):
    A = '-def'

  assert IFoo.test() == 'IFoo-abc'
  assert IBar.test() == 'IBar-def'


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
  if six.PY2:
    assert excinfo.value.errors == ["expected property, got instancemethod: foo"]
  else:
    assert excinfo.value.errors == ["expected property, got function: foo"]


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


def test_instancecheck():

  class IFoo(Interface):
    def foo(self):
      pass

  @implements(IFoo)
  class Bar(object):
    def foo(self):
      return 42

  assert Bar().foo() == 42
  assert IFoo.implemented_by(Bar)
  assert IFoo.provided_by(Bar())
  assert isinstance(Bar(), IFoo)

  class ISpam(IFoo):
    def spam(self):
      pass

  @implements(ISpam)
  class Eggs(object):
    def foo(self):
      return 99
    def spam(self):
      return 42

  assert Eggs().foo() == 99
  assert Eggs().spam() == 42
  assert IFoo.implemented_by(Eggs)
  assert IFoo.provided_by(Eggs())
  assert ISpam.implemented_by(Eggs)
  assert ISpam.provided_by(Eggs())
  assert isinstance(Eggs(), IFoo)
  assert isinstance(Eggs(), ISpam)


def test_implementation_order():
  class IFoo(Interface):
    pass

  impls = []
  for i in range(200):
    @implements(IFoo)
    class Bar(object):
      pass
    impls.append(Bar)

  assert list(IFoo.implementations()) == impls


def test_readme_compound():

  class IFoo(Interface):
    """ The foo interface. """

    x = attr("""Some attribute.""")

    def bar(self, q, r=None):
      """ The bar function. """

  assert set(IFoo) == set(['x', 'bar'])
  assert not hasattr(IFoo, 'x')
  assert not hasattr(IFoo, 'bar')
  assert IFoo['x'].name == 'x'
  assert IFoo['bar'].name == 'bar'

  @implements(IFoo)
  class Foo(object):

    def __init__(self, x=None):
      self.x = x

    def bar(self, q, r=None):
      return q, r, self.x

  assert issubclass(Foo, Implementation)
  assert IFoo.implemented_by(Foo)
  assert IFoo.provided_by(Foo())
  assert list(IFoo.implementations()) == [Foo]
  assert Foo(42).x == 42
