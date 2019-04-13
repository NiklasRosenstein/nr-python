# nr.types

The `nr.types` package provides a number os useful data types for day-to-day
Python programming. It is compatible with Python 2.7 and modern versions of
Python 3.

### Installation

    pip install nr.types

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

<details><summary>Example:</summary>

```python
import nr.types.functools as ft
def test(value):
  def x():
    return value
  return x
x = test(42)
assert x() == 42
y = ft.copy_function(x, closure={'value': 99})
assert y() == 99
```
</details>

#### `nr.types.generic`

Allows you to implement generic types, ie. classes with parameters.

<details><summary>Example:</summary>

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

<details><summary>Example:</summary>

```python
from nr.types.meta import InlineMetaclassBase
class MyClass(InlineMetaclassBase):
  def __metainit__(self, name, bases, attr):
    print('MyClass constructed!')
    self.value = 'foo'
assert MyClass.value == 'foo'
```
</details>

#### `nr.types.record`

Similar to `namedtuple` but mutable, with support for keyword arguments,
type declarations and default values. Supports multiple forms of declaring
a record, eg. via Python 3.6+ class-level annotations, specifying a class-level
`__fields__` member or declaring attributes by creating `record.Field()`
objects.

<details><summary>Example:</summary>

```python
import random
from nr.types import record
class Person(record.Record):
  name: str
  mail: str = None
  age: int = lambda: random.randint(10, 50)

p = Person('John Smith')
assert p.name == 'John Smith'
assert p.mail is None
assert 10 <= p.age <= 50
```
</details>

<details><summary>Alternatives:</summary>

```python
class Person(record.Record):
  name = record.Field(str)
  mail = record.Field(str, None)
  age = record.Field(str, lambda: random.randint(10, 50))

class Person(record.Record):
  __fields__ = [
    ('name', str),
    ('mail', str, None),
    ('age', str, lambda: random.randint(10, 50)),
  ]

Person = record.create_record('Person', [
  ('name', str),
  record.Field.with_name('mail', str, None),
  ('age', str, lambda: random.randint(10, 50))
])
```
</details>

#### `nr.types.sets`

Provides the following set implementations:

* `OrderedSet`

#### `nr.types.stream`

<details><summary>Example:</summary>

```python
from nr.types import stream
stream(range(10)).map(lambda x: x*2)
stream.map(range(10), lambda x: x*2)
```
</details>

#### `nr.types.sumtype`

<details><summary>Example:</summary>

```python
from nr.types import sumtype
class Filter(sumtype):
  Date = sumtype.constructor('min', 'max')
  Keyword = sumtype.constructor('text')

f = Filter.Keyword('building')
assert isinstance(f, Filter)
assert f.is_keyword()
assert f.text == 'building'
```
</details>

<details><summary>Planned Features:</summary>

* Ability to declare constructors like records (see `nr.types.record`)
</details>

---

<p align="center">Copyright &copy; Niklas Rosenstein 2019</p>
