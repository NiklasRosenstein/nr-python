
import abc
import os
import subprocess
import sys
import typing as t

if t.TYPE_CHECKING:
  from . import AWSGIApplication


def get_application_entrypoint(app: t.Union[t.Type['AWSGIApplication'], 'AWSGIApplication']) -> str:
  if not isinstance(app, type):
    app = type(app)
  return app.__module__ + ':' + app.__name__


class AWSGIApplicationLauncher(abc.ABC):

  @abc.abstractmethod
  def launch(self, app: 'AWSGIApplication', entrypoint: t.Optional[str] = None) -> None: ...


class UvicornLauncher(AWSGIApplicationLauncher):
  """
  Launchers your ASGI/WSGI application via Uvicorn.
  """

  # TODO (@NiklasRosenstein): Ensure that Uvicorn access/error logs end up in var/log

  def __init__(self, args: t.Optional[t.List[str]] = None) -> None:
    self._args = args or []

  def launch(self, app: 'AWSGIApplication', entrypoint: t.Optional[str] = None) -> None:
    server = app.config.get().server
    command = ['uvicorn'] + self._args
    if server.host is not None:
      command += ['--host', server.host]
    if server.port is not None:
      command += ['--port', str(server.port)]
    if server.unix_socket is not None:
      command += ['--uds', server.unix_socket]
    if server.workers is not None:
      command += ['--workers', str(server.workers)]
    command += ['nr.appfire.awsgi.launchme:app']
    env = os.environ.copy()
    env['APPFIRE_APP'] = entrypoint or get_application_entrypoint(app)
    try:
      sys.exit(subprocess.call(command, env=env))
    except KeyboardInterrupt:
      sys.exit(1)
