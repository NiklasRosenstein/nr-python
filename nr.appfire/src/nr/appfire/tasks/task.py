
import abc
import enum
import logging
import threading
import types
import typing as t
import typing_extensions as te
import uuid
import weakref

ExcInfoType = t.Tuple[t.Type[BaseException], BaseException, t.Optional[types.TracebackType]]
TaskCallback = t.Callable[['Task'], None]
TaskCallbackCondition = t.Callable[['Task'], bool]


class TaskStatus(enum.Enum):
  """
  Represents the statuses that a task can be in.
  """

  #: The task was created but is not queued for execution.
  PENDING = 0

  #: The task is queued for execution.
  QUEUED = 1

  #: The task is currently running.
  RUNNING = 2

  #: The task has succeeded.
  SUCCEEDED = 3

  #: The task has failed (#Task.error will be set with the Python exception).
  FAILED = 4

  #: The task was queued but then ignored because the queue it was connected to was shut down.
  IGNORED = 5

  @property
  def idle(self) -> bool:
    """
    True if the status is either #PENDING or #QUEUED.
    """

    return self in (TaskStatus.PENDING, TaskStatus.QUEUED)

  @property
  def running(self) -> bool:
    """
    True if the status is #RUNNING.
    """

    return self == TaskStatus.RUNNING

  @property
  def done(self) -> bool:
    """
    True if the status is either #SUCCEEDED, #FAILED or #IGNORED.
    """

    return self in (TaskStatus.SUCCEEDED, TaskStatus.FAILED)

  @property
  def ignored(self) -> bool:
    """
    True if the status is #IGNORED.
    """

    return self == TaskStatus.IGNORED

  @property
  def immutable(self) -> bool:
    """
    Returns `True` if the status represents an immutable task state (same as #done or #ignored).
    """

    return self.done or self.ignored


class TaskCallbacks:
  """
  Container for callbacks that can be added to a task. The callbacks are invoked on every state
  transition of the task.
  """

  class _Entry(t.NamedTuple):
    condition: TaskCallbackCondition
    callback: TaskCallback
    once: bool
    group: t.Optional[str]


  def __init__(self, task: 'Task') -> None:
    self._task = weakref.ref(task)
    self._lock = task._lock
    self._callbacks: t.Dict[str, TaskCallbacks._Entry] = {}

  def __repr__(self) -> str:
    task = self._task()
    assert task is not None
    return f'<_TaskCallbacks task={task.name!r} size={len(self._callbacks)}>'

  def add(
    self,
    condition: TaskCallbackCondition,
    callback: TaskCallback,
    once: bool = True,
    group: t.Optional[str] = None,
  ) -> None:
    """
    Add a callback to the collection. If the *group* is specified, it can be used to remove
    the callbacks from the task wtih #remove_group(). The #condition determines when the *callback*
    will be invoked. If it returns `True` at the time when #add() is used, the *callback* is invoked
    immediately and will not be added to the collection.

    # Arguments
    condition: The condition on which to invoke them *callback*.
    callback: The callback to invoke when the task status is updated and the *condition* matches.
    once: If set to `True`, the callback will be invoked only once and removed from the task after.
    group: A string that identifies the group that the callback belongs to.
    """

    assert callable(callback)
    task = self._task()
    assert task is not None

    with self._lock:
      run_now = condition(task)
      if not run_now:
        self._callbacks[str(uuid.uuid4())] = TaskCallbacks._Entry(condition, callback, once, group)

    if run_now:
      callback(task)

  def remove_group(self, group: str) -> None:
    """
    Remove all callbacks from the collection that belong to the specified *group*.
    """

    with self._lock:
      self._callbacks = {k: e for k, e in self._callbacks.items() if e.group != group}

  def on(
    self,
    state: t.Union[TaskStatus, t.Sequence[TaskStatus], te.Literal['start'], te.Literal['end']],
    callback: TaskCallback,
    once: bool = True,
    group: t.Optional[str] = None,
  ) -> None:
    """
    Adds *callback* to the collection, which will be invoked if the task status is or changes to
    one that is specified via *state*. If *state* is `'end'`, it will match #TaskStatus.SUCCEEDED,
    #TaskStatus.FAILED and #TaskStatus.IGNORED. If the *state* is `'start'`, it behaves the same as
    `'end'` but also match #TaskStatus.RUNNING.
    """

    statuses: t.Sequence[TaskStatus]
    if isinstance(state, str):
      end_statuses = (TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.IGNORED)
      if state == 'start':
        statuses = (TaskStatus.RUNNING,) + end_statuses
      elif state == 'end':
        statuses = end_statuses
      else:
        raise ValueError(f'invalid state: {state!r}')
    elif isinstance(state, TaskStatus):
      statuses = (state,)
    else:
      statuses = state

    def condition(t: 'Task') -> bool:
      return t.status in statuses

    self.add(condition, callback, once, group)

  def _invoke(self) -> None:
    """
    Internal. Invokes all callbacks based on their condition.
    """

    task = self._task()
    assert task is not None

    with self._lock:
      callbacks = self._callbacks.copy()

    remove: t.Set[str] = set()
    for key, entry in callbacks.items():
      try:
        do_run = entry.condition(task)
      except:
        task.log.exception(f'Unhandled exception in callback condition of task "%s": %s', task.name, entry.condition)
        continue
      if not do_run:
        continue
      if entry.once:
        remove.add(key)
      try:
        entry.callback(task)
      except:
        task.log.exception(f'Unhandled exception in callback of task "%s": %s', task.name, entry.callback)

    with self._lock:
      self._callbacks = {k: e for k, e in self._callbacks.items() if k not in remove}


class Task(abc.ABC):
  """
  Abstract class for tasks. Subclasses must implement the #run() method. Make sure to call
  the #Task constructor in your subclass. If you use the #dataclasses module to decorate
  your subclass, you can call the #Task constructor from `__post_init__()`:

  ```py
  from dataclasses import dataclass
  from nr.appfire.tasks import Task

  @dataclass
  class MyTask(Taks):
    # ...

    def __post_init__(self) -> None:
      super().__init__('MyTask')
  ```
  """

  #: The name of the task. There are no requirements about its contents (eg. no uniqueness
  #: or syntax) other than that it is set for every task object.
  name: str

  #: A #logging.Logger created with #logging.getLogger() with the full class name and task name.
  log: logging.Logger

  #: Use this object to manage the callbacks you want to receive for a task. Note that the
  #: executor engine you use to queue the task may make use of the callbacks as well.
  callbacks: TaskCallbacks

  def __init__(self, name: str) -> None:
    self._lock = threading.RLock()
    self.name = name
    self.log = self._create_logger()
    self.callbacks = TaskCallbacks(self)
    self._cancelled = threading.Event()
    self._status = TaskStatus.PENDING
    self._error: t.Optional[ExcInfoType] = None
    self._error_consumed: bool = False

  def _create_logger(self) -> logging.Logger:
    fqn = type(self).__module__ + '.' + type(self).__name__
    return logging.getLogger(f'{fqn}[{self.name}]')

  def _update(self, status: TaskStatus, error: t.Optional[ExcInfoType] = None) -> None:
    """
    Update the status of the task. This should be used only by the executor engine where the task
    is queued. A status change will immediately invoke the registered #callbacks. Some status
    transitions are not allowed (ex. from #TaskStatus.SUCCEEDED to #TaskStatus.RUNNING). In this
    case, a #RuntimeError will be raised. Similarly, if the *status* is #TaskStatus.FAILED but
    no *error* is given, a #RuntimeError will be raised as well.
    """

    if status == TaskStatus.FAILED and error is None:
      raise RuntimeError(f'missing error information for setting task status to FAILED')

    with self._lock:
      if (self._status.immutable and self._status != status) or (self._status == TaskStatus.RUNNING and status.idle):
        raise RuntimeError(f'changing the task status from {self._status.name} to {status.name} is not allowed')
      invoke_callbacks = status != self._status
      old_status = self._status
      self._status = status
      self._error = error

    if invoke_callbacks:
      self.callbacks._invoke()

  @property
  def status(self) -> TaskStatus:
    """
    Returns the current status of the task.
    """

    with self._lock:
      return self._status

  @property
  def error(self) -> t.Optional[ExcInfoType]:
    """
    Returns the exception that occurred while executing the task. This is only set if
    the #status is #TaskStatus.FAILED.
    """

    with self._lock:
      return self._error

  @property
  def error_consumed(self) -> bool:
    """
    Returns #True if the error in the task is marked as consumed.
    """

    with self._lock:
      return self._error_consumed

  def consume_error(self) -> None:
    """
    Mark the error in the task as consumed. This can be called from a callback, but can only be
    called if the #status is #TaskStatus.FAILED.
    """

    with self._lock:
      if self._status != TaskStatus.FAILED:
        raise RuntimeError(f'task status must be FAILED to call Task.consume_error() but is {self._status.name}')
      self._error_consumed = True

  def cancel(self) -> None:
    """
    Set the cancelled flag on the task. After calling this method, #cancelled() will return `True`
    and any thread that is currently using #sleep() will be immediately woken up (rather than
    waiting for the timeout to kick in).
    """

    self._cancelled.set()

  def cancelled(self) -> bool:
    """
    Returns `True` if the task has been cancelled (with the #cancel() methdo). The task subclass
    should use this to check if execution should continue or not.
    """

    if self._cancelled is None:
      raise RuntimeError('Task is not connected to a worker')
    return self._cancelled.is_set()

  def sleep(self, sec: float) -> bool:
    """
    Sleep for *sec* seconds, or until the task is cancelled with the #cancel() method. This should
    be used instead of #time.sleep() inside the task's #run() implementation to ensure quick
    task termination.

    Returns `True` if the task has been cancelled (saving a subsequent call to #cancelled()).
    """

    if self._cancelled is None:
      raise RuntimeError('Task is not connected to a worker')
    return self._cancelled.wait(sec)

  @abc.abstractmethod
  def run(self) -> None: ...
