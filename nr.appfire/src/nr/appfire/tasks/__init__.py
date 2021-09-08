
"""
The `nr.appfire.tasks` package provides an easy-to-use framework for managing background tasks in a
Python application.
"""

from .api import Executor, Runnable, TaskStatus, TaskCallback, Task
from .default import DefaultExecutor

__all__ = [
  'Executor',
  'Runnable',
  'TaskStatus',
  'TaskCallback',
  'Task',
  'DefaultExecutor',
]
