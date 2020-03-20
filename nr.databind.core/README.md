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
