
> Note: This package is in the dangerous land of `0.x.y` versions and may be subject to breaking
> changes with minor version increments.

> This package is superseded by [databind.core](https://pypi.org/project/databind.core/).

# nr.databind.core

The `nr.databind.core` package provides a framework for binding structured data to typed objects
as well as the (de-) serialization of that data from/to other formats.

See also: [nr.databind.json](https://git.niklasrosenstein.com/NiklasRosenstein/nr/src/branch/master/nr.databind.json).

## Example

```py
from nr.databind.core import Field, Struct

class Person(Struct):
    name = Field(str, prominent=True)
    age = Field(int)
    address = Field(int, default=None)

print(Person('John Wick', 48, 'Wicked St.'))  # Person(name='John Wick')
```

---

<p align="center">Copyright &copy; 2020 Niklas Rosenstein</p>
