
import dataclasses
import logging
import queue
import sys
import threading
import typing as t

from .task import ExcInfoType, Task, TaskStatus
from .util import AtomicCounter

log = logging.getLogger(__name__)


@dataclasses.dataclass
class Worker:
  """
  The worker thread accepts tasks from a queue and executes them. Receiving #None from the queue
  indicates to the worker that its should stop.
  """

  #: The name of the worker is used as the thread name.
  name: str

  #: The queue to retrieve new tasks from.
  queue: 'queue.Queue[t.Optional[Task]]'

  def __post_init__(self) -> None:
    self._thread = threading.Thread(target=self._run, name=self.name, daemon=True)
    self._lock = threading.Lock()
    self._current_task: t.Optional[Task] = None

  def __repr__(self) -> str:
    return f'Worker(name={self.name!r})'

  def _run(self) -> None:
    log.info('Start worker %s', self.name)

    while True:
      task = self.queue.get()
      if task is None:
        self.queue.task_done()
        break
      with self._lock:
        self._current_task = task
      try:
        self._run_task(task)
      finally:
        with self._lock:
          self._current_task = None

    log.info('Stopped worker %s', self.name)

  def _run_task(self, task: Task) -> None:
    log.info('Running task "%s"', task.name)

    try:
      task._update(TaskStatus.RUNNING)
      task.run()
    except:
      task._update(TaskStatus.FAILED, t.cast(ExcInfoType, sys.exc_info()))
      if not task._error_consumed:
        log.exception('Unhandled exception in task "%s"', task.name)
    else:
      task._update(TaskStatus.SUCCEEDED)

  def get_current_task(self) -> t.Optional[Task]:
    with self._lock:
      return self._current_task

  def start(self) -> None:
    self._thread.start()


@dataclasses.dataclass
class TaskManager:
  """
  The task manager is responsible for managing the execution of tasks in the background. It
  accomplishes this by managing a bounded list of #Worker threads as per the configured
  #max_workers. Tasks can also be run in dedicated workers if they should not block a spot in
  the pool.
  """

  _CALLBACK_GROUP = '_TaskManager'

  #: The name of the task manager. This is used as the prefix for created #Worker names.
  name: str

  #: The maximum number of workers to spawn. Defaults to 8,
  max_workers: int = 8

  def __post_init__(self) -> None:
    #: A list of the workers assigned to the pool that is bounded by #max_size.
    self._pool_workers: t.List[Worker] = []

    #: A list of dedicated workers that have been spawned with #dedicated().
    self._dedicated_workers: t.List[Worker] = []

    #: The queue that is used to send tasks to the workers.
    self._queue: 'queue.Queue[t.Optional[Task]]' = queue.Queue()

    #: A counter for all tasks submitted to the task manager that have not yet completed.
    self._all_tasks = AtomicCounter()

    #: A counter for all currently active tasks.
    self._active_tasks = AtomicCounter()

    self._lock = threading.Lock()
    self._shutdown = False

  def _prepare_task(self, task: Task, queue: queue.Queue) -> None:
    self._all_tasks.inc()
    task.callbacks.on('start', lambda _t: self._active_tasks.inc(), group=self._CALLBACK_GROUP + '|Active inc')
    task.callbacks.on('end', lambda _t: queue.task_done(), group=self._CALLBACK_GROUP + '|Queue done')
    task.callbacks.on('end', lambda _t: self._active_tasks.dec(), group=self._CALLBACK_GROUP + '|Active dec')
    task.callbacks.on('end', lambda _t: self._all_tasks.dec(), group=self._CALLBACK_GROUP + '|All dec')
    task.callbacks.on('end', lambda _t: task.callbacks.remove_group(self._CALLBACK_GROUP), group=self._CALLBACK_GROUP + '|Remove')
    task._update(TaskStatus.QUEUED)

  def queue(self, task: Task) -> None:
    """
    Queue a task for execution in the worker pool. If there is a free slot in the pool and all
    existing workers are busy, a new worker will be spawned immediately.
    """

    assert isinstance(task, Task)
    assert hasattr(task, 'name')  # common mistake when subclassing with @dataclass

    if self._shutdown:
      raise RuntimeError('task manager is shut down')

    self._prepare_task(task, self._queue)
    self._queue.put(task)
    size = self._all_tasks.get()
    if size >= len(self._pool_workers) and size < self.max_workers:
      self._spawn_pool_worker()

  def _spawn_pool_worker(self) -> None:
    worker = Worker(f'{self.name}-Worker-{len(self._pool_workers)}', self._queue)
    worker.start()
    self._pool_workers.append(worker)

  def dedicated(self, task: Task) -> None:
    """
    Run the given *task* in a dedicated worker. The task will not count towards the #max_worker
    limit as it will be assigned to its own dedicated worker which will also stop when the task
    is finished.
    """

    assert isinstance(task, Task)
    assert hasattr(task, 'name')  # common mistake when subclassing with @dataclass

    if self._shutdown:
      raise RuntimeError('task manager is shut down')

    private_queue: 'queue.Queue[t.Optional[Task]]' = queue.Queue()
    private_queue.put(task)
    private_queue.put(None)

    self._prepare_task(task, private_queue)

    worker = Worker(f'{self.name}-DedicatedWorker-{len(self._dedicated_workers)}', private_queue)
    self._dedicated_workers.append(worker)
    task.callbacks.on('end', lambda _t: self._dedicated_workers.remove(worker), group=self._CALLBACK_GROUP)
    worker.start()

  def shutdown(self) -> None:
    """
    Shut down the task manager, marking currently running tasks as cancelled.
    Any queued tasks will ignored. Blocks until all tasks have been processed.
    """

    if self._shutdown:
      raise RuntimeError('shut down already initiated or completed')
    self._shutdown = True

    log.info('Sending shutdown signal to workers')

    for worker in self._pool_workers:
      task = worker.get_current_task()
      if task is not None:
        task.cancel()
      self._queue.put(None)

    for worker in self._dedicated_workers:
      task = worker.get_current_task()
      if task is not None:
        task.cancel()

    self._all_tasks.join()

  def idlejoin(self, catch_keyboard_interrupt: bool = True) -> None:
    """
    Wait until all tasks in the task manager are completed without prematurely shutting down the
    workers, thus allowing currently pending tasks (or tasks that continue to be queued) to run.

    By default, this method catches #KeyboardInterrupt exceptions and subsequently shuts down the
    task manager.
    """

    try:
      self._all_tasks.join()
    except KeyboardInterrupt:
      if catch_keyboard_interrupt:
        log.info('Caught KeyboardInterrupt')
        self.shutdown()
      else:
        raise
