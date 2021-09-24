
import abc
import dataclasses
import importlib
import os
import subprocess
import sys
import typing as t

from nr.appfire.application import Application


@t.runtime_checkable
class ASGIApp(t.Protocol):

  def __call__(self, scope, receive, send): ...


@t.runtime_checkable
class WSGIApp(t.Protocol):

  def __call__(self, environ, start_response): ...


@t.runtime_checkable
class AWSGIAppProvider(t.Protocol):

  def get_app(self) -> t.Union[ASGIApp, WSGIApp]: ...


def app() -> t.Union[ASGIApp, WSGIApp]:
  """
  Loads an #nr.appfire.application.Application class per the `APPFIRE_APP` or `AF_APP` environment variable. That
  application class must implement the #AWSGIAppProvider interface. The application will be initialized and
  subsequently the result of #AWSGIAppProvider.get_app() will be returned.

  This function is supposed to be used as the entrypoint for production ASGI/WSGI servers. Examples:

  * `AF_APP=myapp:MyApp gunicorn --workers=2 'nr.appfire.awsgi:app()'`
  * `APPFIRE_APP=myapp:MyApp uvicorn --host 0.0.0.0 --port 1337 --factory 'nr.appfire.awsgi:app'`

  If an `APPFIRE_HOME` or `AF_HOME` variable is set, the function will change to the given directory before returning
  the ASGI or WSGI application instance.
  """

  home = next(filter(bool, [os.environ.pop('APPFIRE_HOME', None) or os.environ.pop('AF_HOME', None)]), None)
  if home is not None:
    os.chdir(home)

  entrypoint = next(filter(bool, [os.environ.pop('APPFIRE_APP', None) or os.environ.pop('AF_APP', None)]), None)
  if not entrypoint:
    raise EnvironmentError('missing APPFIRE_APP or AF_APP environment variable.')

  module_name, class_name = entrypoint.split(':')
  module = importlib.import_module(module_name)
  class_ = getattr(module, class_name)

  if not issubclass(class_, AWSGIAppProvider):
    raise TypeError(f'{entrypoint!r} does not implement the AWSGIAppProvider protocol.')

  if not issubclass(class_, Application):
    raise TypeError(f'{entrypoint!r} is not a subclass of Application.')

  application = class_()
  application.initialize()
  return application.get_app()


def entrypoint_for(app: t.Type) -> str:
  """
  Returns the entrypoint in `module:class` form for the given type.
  """

  return app.__module__ + ':' + app.__name__


class AWSGILauncher(abc.ABC):
  """
  Interface for AWSGI/WSGI application launchers.
  """

  @abc.abstractmethod
  def launch(self, entrypoint: t.Optional[str] = None) -> None: ...


@dataclasses.dataclass
class UvicornLauncher(AWSGILauncher):
  """
  Launches your ASGI/WSGI application via Uvicorn.
  """

  # TODO (@NiklasRosenstein): Ensure that Uvicorn access/error logs end up in var/log

  #: Bind socket to this host.
  host: t.Optional[str] = None

  #: Bind socket to this port.
  port: t.Optional[int] = 8000

  #: Bind to a UNIX domain socket.
  unix_socket: t.Optional[str] = None

  #: Number of worker processes.
  workers: t.Optional[int] = None

  #: Enable auto-reload.
  reload: bool = False

  #: Event loop implementation.
  loop: str = 'auto'

  #: HTTP protocol implementation.
  http: str = 'auto'

  #: Additional keyword arguments for the Uvicorn invokation.
  kwargs: t.Dict[str, t.Any] = dataclasses.field(default_factory=dict)

  def launch(self, entrypoint: str) -> None:
    assert isinstance(entrypoint, str), type(entrypoint)

    os.environ['APPFIRE_APP'] = entrypoint

    import uvicorn
    try:
      sys.exit(uvicorn.run(
        __name__ + ':app',
        host=self.host,
        port=self.port,
        uds=self.unix_socket,
        workers=self.workers,
        reload=self.reload,
        loop=self.loop,
        http=self.http,
        factory=True,
        **self.kwargs
      ))
    except KeyboardInterrupt:
      sys.exit(1)


def launch(app: t.Union[str, t.Type[Application]], type_: str, **kwargs) -> None:
  launchers[type_](**kwargs).launch(app if isinstance(app, str) else entrypoint_for(app))


launchers = {
  'uvicorn': UvicornLauncher,
}
