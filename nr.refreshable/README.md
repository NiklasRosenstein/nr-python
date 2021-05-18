# nr.refreshable

Provides the `Refreshable` class. A refreshable is a thread-safe container for a value that changes
over time. Refreshables can be subscribed to, to be notified when they are updated, and mapped to
compute new values and cache them as the parent gets updated.

__Example__

```py
from nr.refreshable import Refreshable

root = Refreshable(42)
child = root.map(lambda n: n + 10)
assert child.get() == 52
root.update(100)
assert child.get() == 110
```

---

<p align="center">Copyright &copy; 2021 Niklas Rosenstein</p>
