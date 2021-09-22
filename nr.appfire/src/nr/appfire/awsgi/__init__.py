
"""
ASGI/WSGI specific application base class.
"""

import abc
import typing as t

from ..application import Application
from .config import AWSGIApplicationConfig, T_AWSGIApplicationConfig


class AWSGIApplication(Application[T_AWSGIApplicationConfig]):
  """
  Base class for ASGI/WSGI applications. Can be used with the `nr.appfire.application.awsgi` entrypoint
  or launched using an #AWSGILauncher.
  """

  @abc.abstractmethod
  def get_application(self) -> t.Any:
    """
    Return the ASGI/WSGI application to serve.
    """

__all__ = ['AWSGIApplication', 'AWSGIApplicationConfig']
