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
