## nr.sumtype

Make use of sumtypes in Python.

```python
from nr.sumtype import Constructor, Sumtype

class Status(Sumtype):
  Idle = Constructor()
  Loading = Constructor(['progress'])
  Succeeded = Constructor()
  Error = Constructor(['message'])

print(Status.Loading(progress=0.0))
```
