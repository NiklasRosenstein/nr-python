
import dataclasses
import time
from nr.appfire.tasks import Runnable, Task, DefaultExecutor
from nr.appfire.tasks.api import TaskStatus


@dataclasses.dataclass
class Sleeper(Runnable[None]):
  duration: float

  def run(self, task: 'Task') -> None:
    task.sleep(self.duration)


def test_default_executor_shutdown_no_active_cancel():
  executor = DefaultExecutor('Test', 2)
  t1 = executor.execute(Sleeper(0.5), 'one')
  t2 = executor.execute(Sleeper(0.5), 'two')
  executor.shutdown(False)
  assert t1.status == TaskStatus.SUCCEEDED
  assert t2.status == TaskStatus.QUEUED


def test_default_executor_shutdown_active_cancel():
  executor = DefaultExecutor('Test', 1)
  t1 = executor.execute(Sleeper(10))
  tstart = time.perf_counter()
  time.sleep(0.5)
  executor.shutdown(True)
  tdelta = time.perf_counter() - tstart
  assert tdelta < 0.6
  assert t1.status == TaskStatus.CANCELLED


def test_default_executor_task_join():
  executor = DefaultExecutor('Test', 1)
  t1 = executor.execute(Sleeper(0.1))
  t1.join()
  assert t1.status == TaskStatus.SUCCEEDED
