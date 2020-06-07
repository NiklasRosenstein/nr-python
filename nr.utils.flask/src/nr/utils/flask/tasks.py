# Copyright (c) 2018 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

"""
This modules provides a framework for managing background tasks in a Flask application.
"""

from nr.interface import Interface, default, implements, override
from typing import Any, Callable, Union
import flask
import enum
import logging
import queue
import threading
import time

logger = logging.getLogger(__name__)


class IScheduler(Interface):

  def start(self) -> None:
    ...

  def stop(self, wait: bool = True) -> None:
    ...

  def schedule(self, func: Callable[[], Any], at: int) -> None:
    ...


@implements(IScheduler)
class ThreadedScheduler(threading.Thread):
  """
  An implementation of the #IScheduler interface that runs as a daemon thread.
  """

  def __init__(self):
    super(ThreadedScheduler, self).__init__()
    self.daemon = True
    self.queue = queue.PriorityQueue()
    self.cond = threading.Condition()
    self.stop_event = threading.Event()

  @override
  def schedule(self, func: Callable[[], Any], at: int) -> None:
    with self.cond:
      self.queue.put((at, func))
      self.cond.notify()

  @override
  def stop(self, wait: bool = True) -> None:
    with self.cond:
      self.stop_event.set()
      self.cond.notify()

  def stopped(self) -> bool:
    return self.stop_event.is_set()

  def run(self) -> None:
    logger.info('SchedulerThread started.')
    while not self.stop_event.is_set():
      at, func = self.queue.get()
      delta = at - time.time()
      if delta <= 0:
        try:
          func()
        except Exception:
          logger.exception('Error calling scheduled function %r.', func)
        continue
      with self.cond:
        self.cond.wait(delta)
        self.queue.put((at, func))


class Restart(enum.Enum):
  no = 0
  on_failure = 1
  on_success = 2
  always = 3


class TaskImpl:
  """
  Can be subclasses to implement tasks. #TaskImpl objects have a reference to the #Task
  object that is managed by the scheduler, thus allowing the task implementation to check
  if the task was stopped.
  """

  _task = None
  _func = None
  _pass_task = False

  def __init__(self, func: Callable = None, pass_task: bool = False) -> None:
    self._func = func
    self._pass_task = pass_task

  def stopped(self) -> bool:
    return self.task.stopped()

  def run(self):
    if not self._func:
      raise NotImplementedError('{}.run()'.format(type(self).__name__))
    if not self.task:
      raise RuntimeError('TaskImpl._task is not set.')
    if self._pass_task:
      self._func(self._task)
    else:
      self._func()


class Task:

  def __init__(
    self,
    id_: str,
    impl: TaskImpl,
    restart: Restart,
    restart_cooldown: int,
    pass_task: bool,
    scheduler: IScheduler,
  ) -> None:
    self.id = id_
    self.impl = impl
    self.restart = restart
    self.restart_cooldown = restart_cooldown
    self.pass_task = pass_task
    self.scheduler = scheduler
    self.thread = None
    self.started_count = 0
    self.lock = threading.RLock()
    self.finished_callbacks = []
    self.stop_event = threading.Event()

  def __repr__(self) -> str:
    return 'Task(id={!r}, restart={!r})'.format(self.id, self.restart)

  def _run(self) -> None:
    try:
      try:
        self.impl._task = self
        self.impl.run()
      finally:
        self.impl._task = None
      success = True
    except Exception:
      logger.exception('Exception in task %r (restart: %s)', self.id, self.restart)
      success = False
    finally:
      for callback in self.finished_callbacks:
        try:
          callback()
        except Exception:
          logger.exception('Exception in callback of task %r (callback: %r)', self.id, callback)
    with self.lock:
      self.thread = None
      if (success and self.restart == Restart.on_success) or \
          (not success and self.restart == Restart.on_failure) or \
          self.restart == Restart.always:
        self.scheduler.schedule(self.start, time.time() + self.restart_cooldown)

  def start(self) -> None:
    with self.lock:
      if self.thread and self.thread.isAlive():
        raise RuntimeError('Task.thread is still alive')
      self.thread = threading.Thread(target=self._run)
      self.thread.start()
      self.started_count += 1
      self.stop_event.clear()
      logger.info('Started task %r (thread-id: %s, started-count: %s)',
        self.id, self.thread.ident, self.started_count)

  def stop(self) -> None:
    self.stop_event.set()

  def add_finished_callback(self, func: Callable[[], Any]) -> None:
    self.finished_callbacks.append(func)


class TaskManager:
  """
  Manager class for background tasks.
  """

  def __init__(self, scheduler: IScheduler = None):
    self.scheduler = scheduler or ThreadedScheduler()
    self.tasks = {}

  def get_task(self, id_: str) -> Task:
    try:
      return self.tasks[id_]
    except KeyError:
      raise ValueError('unknown task {!r}'.format(id_))

  def register_task(
    self,
    id_: str,
    task_impl: Union[TaskImpl, Callable[[], Any]],
    start_immediately: bool = False,
    restart: Union[Restart, str] = Restart.always,
    restart_cooldown: int = 0,
    pass_task: bool = False,
  ) -> Task:
    """
    Add a task to the server that will be started on the first request to the application,
    or immediately if *start_immediately* is set to True. If *restart* is set to True, the
    task will be restarted when it ended.
    """

    if not isinstance(task_impl, TaskImpl):
      task_impl = TaskImpl(task_impl)

    if isinstance(restart, str):
      restart = Restart[restart.lower().replace('-', '_')]

    if id_ in self.tasks:
      raise ValueError('task id {!r} already occupied'.format(id_))
    task = Task(id_, task_impl, restart, restart_cooldown, pass_task, self.scheduler)
    self.tasks[id_] = task
    logger.info('Registered task %r.', id_)
    if start_immediately:
      task.start()
    return task

  def unregister_task(self, id_: str) -> None:
    """
    Removes a task from the manager by id. Raises a #ValueError if there is no task with
    the specified id. A stop event will be sent to the #Task unless *stop* is #False.
    """

    if id_ not in self.tasks:
      raise ValueError('unknown task {!r}'.format(id_))

    task = self.tasks.pop(id_)
    task.restart = Restart.No
    task.stop()

  def start(self):
    self.scheduler.start()
    for task in self.tasks.values():
      if task.started_count == 0:
        task.start()

  def stop(self):
    self.scheduler.stop()
    for task in self.tasks.values():
      task.stop()
