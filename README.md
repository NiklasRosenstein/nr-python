# nr.types

[![CircleCI](https://circleci.com/gh/NiklasRosenstein/python-nr.types.svg?style=svg)](https://circleci.com/gh/NiklasRosenstein/python-nr.types)

The `nr.types` package provides a number os useful data types for day-to-day
Python programming. It is compatible with Python 2.7 and modern versions of
Python 3.

### Installation

    pip install nr.types

### Run Tests

    pip install -e .[test]
    pytest --cov=./src/nr

### API

#### `nr.types.NotSet`

The `NotSet` singleton is useful in cases where `None` is an acceptable value
for a parameter so there needs to be an additional state that defines the
parameter as "not set".

#### `nr.types.abc`

An alias for `collections.abc` or `collections` (the `six` module does not
provide a move for these modules).

#### `nr.types.functools`

Tools to help with Python function internals such as closures, code
and function objects.

<details doctest name='functools.example'><summary>Example:</summary>

```python
from nr.types.utils.function import copy_function
def test(value):
  def x():
    return value
  return x
x = test(42)
assert x() == 42
y = copy_function(x, closure={'value': 99})
assert y() == 99
```
</details>

#### `nr.types.generic`

Allows you to implement generic types, ie. classes with parameters.

<details doctest name='generic.example'><summary>Example:</summary>

```python
from nr.types import generic
class HashDict(generic.Generic['key_hash']):
  def __init__(self):
    generic.assert_initialized(self)
    self.data = {}
  def __getitem__(self, key):
    return self.data[self.key_hash(key)]
  def __setitem__(self, key, value):
    self.data[self.key_hash(key)] = value
UnsafeHashDict = HashDict[hash]
```
</details>

#### `nr.types.interface`

Similar to `zope.interface`, but Python 3 compatible and less magical.

<details doctest name="interface.example"><summary>Example:</summary>

```python
from nr.types.interface import Interface, Implementation, implements, attr

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
```
</details>


#### `nr.types.maps`

Provides the following mapping (and mapping-related) implementations:

* `OrderedDict`
* `ObjectAsDict`
* `ObjectFromDict`
* `ChainDict` (use `maps.chain()`)
* `HashDict[hash_func]`
* `ValueIterableDict`

#### `nr.types.meta`

Provides useful metaclasses, such as `InlineMetaclass`.

<details doctest name='meta.example'><summary>Example:</summary>

```python
from nr.types.meta import InlineMetaclassBase
class MyClass(InlineMetaclassBase):
  def __metainit__(self, name, bases, attr):
    print('MyClass constructed!')
    self.value = 'foo'
assert MyClass.value == 'foo'
```
</details>

#### `nr.types.moduletools`

Provides some tools for working with modules. Currently only provides the
`make_inheritable()` function which can be used from within your module to
make the module object itself usable as a parent class.

```python
# myclass.py
class MyClass(object): pass
make_inheritable(__name__)

# test.py
import myclass
class MySubclass(myclass): pass
assert issubclass(MySubclass, myclass.MyClass)
```


#### `nr.types.proxy`

Provides the `proxy` class which is a wrapper for a callable. Any kind of
access to the proxy object is redirected to the object returned by the
callable.

<details doctest name="proxy"><summary>Example for `proxy` class:</summary>

```python
from nr.types.proxy import proxy_decorator

count = 0

@proxy_decorator()
def auto_increment():
  global count
  count += 1
  return count

assert auto_increment == 1
assert auto_increment == 2
assert auto_increment + 10 == 13
```
</details>

<details doctest name="proxy.lazy"><summary>Example for `proxy` class:</summary>

```python
from nr.types.proxy import proxy_decorator

count = 0

@proxy_decorator(lazy=True)
def not_incrementing():
  global count
  count += 1
  return count

assert not_incrementing == 1
assert not_incrementing == 1
assert not_incrementing == 1
```
</details>


#### `nr.types.sets`

Currently only provides an `OrderedSet` implementation.

#### `nr.types.stream`

<details doctest name='stream.example'><summary>Example:</summary>

```python
from nr.types.stream import Stream
Stream(range(10)).map(lambda x: x*2)
Stream.map(range(10), lambda x: x*2)
```
</details>

#### `nr.types.structured`

<details doctest name='structured.example'><summary>Example:</summary>

```python
from nr.types import structured

Person = structured.ForwardDecl('Person')
People = structured.translate_field_type({Person})
class Person(structured.Object):
  name = structured.ObjectKeyField()
  age = structured.Field(int)
  numbers = structured.Field([str])

data = {
  'John': {'age': 52, 'numbers': ['+1 123 5423435']},
  'Barbara': {'age': 29, 'numbers': ['+44 1523/5325323']}
}
people = structured.extract(data, People)
assert people['John'] == Person('John', 52, ['+1 123 5423435'])
assert people['Barbara'] == Person('Barbara', 29, ['+44 1523/5325323'])
```
</details>

#### `nr.types.sumtype`

<details doctest name='sumtype.example'><summary>Example:</summary>

```python
from nr.types.sumtype import Constructor, Sumtype, member_of
from nr.types.structured import Field, Object

class Filter(Sumtype):
  # Three ways to define constructors.
  # 1)
  Date = Constructor('min,max')
  # 2)
  Keyword = Constructor([
    Field(str, name='text')
  ])
  # 3)
  @Constructor
  class Duration(Object):
    value = Field(int, default=3600)
    def to_hours(self):
      return self.value / 3600.0

  # Enrich constructors with members.
  @member_of([Date, Keyword])
  def only_on_date_or_keyword(self):
    return 'The answer is 42'

f = Filter.Keyword('building')
assert isinstance(f, Filter)
assert f.is_keyword()
assert f.text == 'building'
assert hasattr(f, 'only_on_date_or_keyword')
assert f.only_on_date_or_keyword() == 'The answer is 42'

f = Filter.Date(10, 42)
assert isinstance(f, Filter)
assert f.is_date()
assert (f.min, f.max) == (10, 42)
assert hasattr(f, 'only_on_date_or_keyword')
assert f.only_on_date_or_keyword() == 'The answer is 42'

f = Filter.Duration()
assert isinstance(f, Filter)
assert f.is_duration()
assert f.value == 3600
assert not hasattr(f, 'only_on_date_or_keyword')

f = Filter.Duration(value=4759)
assert f.value == 4759
assert f.to_hours() == (4759 / 3600.0)
```
</details>

---

<p align="center">Copyright &copy; Niklas Rosenstein 2019</p>
