# nr.appfire

Appfire is a toolkit that provides utilities for quickly building configurable microservices.

## Components

### `nr.appfire.tasks`

This package provides an easy-to-use framework for managing background tasks in a Python application.

__Example__

```py
from dataclasses import dataclass
from nr.appfire.tasks import Task, TaskManager

@dataclass
class MyTask(Task):
  loops: int

  def __post_init__(self) -> None:
    super().__init__(f'MyTask[loops={self.loops}]')

  def run(self) -> None:
    for i in range(self.loops):
      if self.cancelled():
        return
      print(i)
      self.sleep(1)

manager = TaskManager('MyApp')
manager.queue(MyTask(10))
manager.idlejoin()
```

---

<p align="center">Copyright &copy; 2021 Niklas Rosenstein</p>
