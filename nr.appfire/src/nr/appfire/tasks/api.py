
import abc
import enum
import logging
import types
import typing as t
import typing_extensions as te

ExcInfoType = t.Tuple[t.Type[BaseException], BaseException, t.Optional[types.TracebackType]]
TaskCallback = t.Callable[['Task'], None]
TaskCallbackCondition = t.Callable[['Task'], bool]


class Runnable(abc.ABC):
  """
  Abstract representation of something that can be run, for example in a task. Depending on the
  use case, runnables may need to be serializable.
  """

  @abc.abstractmethod
  def run(self, task: 'Task') -> None: ...


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


class TaskCallbacks(abc.ABC):

  @abc.abstractmethod
  def add(
    self,
    condition: TaskCallbackCondition,
    callback: TaskCallback,
    once: bool = True,
    group: t.Optional[str] = None,
  ) -> None:
    """
    Add a callback to the task. If the *group* is specified, it can be used to remove the callbacks
    from the task wtih #remove_group(). The #condition determines when the *callback* will be invoked.
    If it returns `True` at the time when #add() is used, the *callback* is invoked immediately and
    will not be added to the collection.

    # Arguments
    condition: The condition on which to invoke them *callback*.
    callback: The callback to invoke when the task status is updated and the *condition* matches.
    once: If set to `True`, the callback will be invoked only once and removed from the task after.
    group: A string that identifies the group that the callback belongs to.
    """

  @abc.abstractmethod
  def remove(self, *, group: str) -> None:
    """
    Remove all callbacks from the collection that belong to the specified *group*.
    """

  def on(
    self,
    state: t.Union[TaskStatus, t.Sequence[TaskStatus], te.Literal['start'], te.Literal['end']],
    callback: TaskCallback,
    once: bool = True,
    group: t.Optional[str] = None,
  ) -> None:
    """
    Adds *callback* to the collection, which will be invoked if the task status is or changes to one
    that is specified via *state*. If *state* is `'end'`, it will match #TaskStatus.SUCCEEDED,
    #TaskStatus.FAILED and #TaskStatus.IGNORED. If the *state* is `'start'`, it behaves the same as
    # `'end'` but also match #TaskStatus.RUNNING.
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


class Executor(abc.ABC):
  """
  Interface for task managers that can dispatch tasks for execution.
  """

  @abc.abstractmethod
  def get_worker_count(self) -> int: ...

  @abc.abstractmethod
  def get_idle_worker_count(self) -> int: ...

  @abc.abstractmethod
  def execute(
    self,
    runnable: Runnable,
    name: t.Optional[str] = None,
    at: t.Optional[float] = None,
  ) -> 'Task':
    """
    Execute the given *runnable* object in the task manager.

    # Arguments
    runnable: The runnable to invoke. Depending on the implementation of the task manager, this object
      may need to be serializable with whatever serializer the implementation is using (in case of a
      distributed task manager).
    name: An optional name for the runnable. If not specified, the #repr() of the object will be used.
    at: The timestamp at which the runnable is supposed to be executed. If the timestamp is smaller than
      the current time or if the parameter is not set, it will be executed immediately.

    # Returns
    The #Task object for this runnable.
    """

  @abc.abstractmethod
  def shutdown(self, cancel_running_taks: bool = True, block: bool = True) -> None:
    """
    Shut down the task manager, preventing new tasks from being exexuted. if *cancel_running_tasks*
    is enabled, all currently running tasks will be cancelled. By default, the method blocks until
    all running tasks have exited.

    This method may raise a #RuntimeError if it was called before.
    """

  @abc.abstractmethod
  def join(self) -> None:
    """
    Block until all pending and currently running tasks have been processed.
    """

  def idlejoin(self) -> None:
    """
    Like #join(), but garuantee a call to #shutdown() in the end.
    """

    try:
      self.join()
    finally:
      self.shutdown()


class Task(abc.ABC):
  """
  Abstract representation of a task.
  """

  Status = TaskStatus
  Callback = TaskCallback
  Runnable = Runnable
  Executor = Executor

  @abc.abstractproperty
  def id(self) -> str: ...

  @abc.abstractproperty
  def worker_id(self) -> t.Optional[str]: ...

  @abc.abstractproperty
  def name(self) -> str: ...

  @abc.abstractproperty
  def logger(self) -> logging.Logger: ...

  @abc.abstractproperty
  def callbacks(self) -> TaskCallbacks: ...

  @property
  def status(self) -> TaskStatus: ...

  @property
  def error(self) -> t.Optional[ExcInfoType]: ...

  @property
  def error_consumed(self) -> bool: ...

  @abc.abstractmethod
  def consume_error(self, origin: t.Optional[str] = None) -> None: ...

  @abc.abstractmethod
  def cancel(self) -> None: ...

  @abc.abstractmethod
  def cancelled(self) -> bool:
    """
    Returns `True` if the task has been cancelled.
    """

  @abc.abstractmethod
  def sleep(self, duration: float) -> bool:
    """
    Sleep for *duration* seconds or until the task is cancelled.

    Returns `True` if the sleep completed, `False` is the timeout triggered which means
    that the task has been cancelled.
    """
