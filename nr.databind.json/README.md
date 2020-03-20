# nr.databind.json

The `nr.databind.json` package implements (de-) serializers for nested payloads that usually
result from loading JSON-formatted data.

See also [nr.databind.core](https://git.niklasrosenstein.com/NiklasRosenstein/nr/src/branch/master/nr.databind.core).

## Example

```py
from nr.databind.core import Field, Struct, ObjectMapper
from nr.databind.json import JsonModule

class Person(Struct):
    name = Field(str, prominent=True)
    age = Field(int)
    address = Field(int, default=None)

mapper = ObjectMapper(JsonModule())
print(mapper.deserialize({'name': 'John Wick', 'age': 48, 'address': 'Wicked St.'}))  # Person(name='John Wick')
```
