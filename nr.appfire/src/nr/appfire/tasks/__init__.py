
"""
The `nr.appfire.tasks` package provides an easy-to-use framework for managing background tasks in a
Python application.
"""

from .api import TaskStatus, TaskCallback, Task, TaskManager, Runnable
from .default import DefaultTaskManager
