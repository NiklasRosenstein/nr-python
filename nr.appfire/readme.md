# nr.appfire

Appfire is a toolkit that provides utilities for quickly building configurable microservices.

## Components

### `nr.appfire.tasks`

This package provides an easy-to-use framework for managing background tasks in a Python application.

__Example__

```py
import dataclasses
from nr.appfire.tasks import Runnable, Task, DefaultExecutor

@dataclasses.dataclass
class Looper(Runnable[None]):
  loops: int

  def run(self, task: Task[None]) -> None:
    for i in range(self.loops):
      print(i)
      if not task.sleep(1):
        print('Bye, bye')
        break

executor = DefaultExecutor('MyApp')
executor.execute(Looper(10))
executor.idlejoin()
```

---

<p align="center">Copyright &copy; 2021 Niklas Rosenstein</p>
