
> Note: This package is in the dangerous land of `0.x.y` versions and may be subject to breaking
> changes with minor version increments.

# nr.stream

Provides a `Stream` class which allows chained operations on a stream of values.

## Example

```py
from nr.stream import Stream

values = [3, 6, 4, 7, 1, 2, 5]
assert list(Stream(values).chunks(values, 3, fill=0).map(sum)) == [13, 10, 5]
```

---

<p align="center">Copyright &copy; 2020 Niklas Rosenstein</p>

