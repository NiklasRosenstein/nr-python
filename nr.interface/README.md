
> Note: This package is in the dangerous land of `0.x.y` versions and may be subject to breaking
> changes with minor version increments.

> __Important__: Development of `nr.interface` is discontinued. We recommend to use the `abc`
> module instead.

# nr.interface

Interface definitions for Python. Inspired by `zope.interface`.

## Quickstart

```py
from nr.interface import Interface, implements, override

class Pet(Interface):

  def make_sound(self) -> str:
    pass

@implements(Pet)
class Dog:

  @override
  def make_sound(self) -> str:
    return 'Bark!'

assert 'make_sound' in Pet.members
assert Pet.implemented_by(Dog)
assert list(Pet.implementations()) == [Dog]
```

---

<p align="center">Copyright &copy; 2020 Niklas Rosenstein</p>
