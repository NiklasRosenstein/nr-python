
> Note: This package is in the dangerous land of `0.x.y` versions and may be subject to breaking
> changes with minor version increments.

# nr.sumtype

Sumtypes in Python.

### Example

```python
from nr.sumtype import Constructor, Sumtype

class Status(Sumtype):
  Idle = Constructor()
  Loading = Constructor(['progress'])
  Succeeded = Constructor()
  Error = Constructor(['message'])

print(Status.Loading(progress=0.0))
```

---

<p align="center">Copyright &copy; 2020 Niklas Rosenstein</p>
