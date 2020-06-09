# -*- coding: utf-8 -*-
# Copyright (c) 2020 Niklas Rosenstein
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

from importlib import import_module
from nr.databind.core import Field, ObjectMapper, SerializeAs, Struct, UnionType
from nr.databind.json import JsonModule, JsonSerializer
from nr.interface import default, implements, Interface, override
from nr.utils.process import process_exists, process_terminate, replace_stdio, spawn_daemon
from typing import Any, Optional, TextIO, Tuple, Type
import enum
import functools
import logging
import os
import subprocess
import yaml

logger = logging.getLogger(__name__)


@JsonSerializer(deserialize='_BindConfig__deserialize')
class BindConfig(Struct):
  host = Field(str)
  port = Field(int)

  @classmethod
  def __deserialize(cls, context, node):
    if not isinstance(node.value, str):
      raise NotImplementedError
    host, port = node.value.partition(':')
    try:
      port = int(port)
    except ValueError as exc:
      raise node.value_error(exc)
    return cls(host, port)


class SslConfig(Struct):
  cert = Field(str)
  key = Field(str)


@JsonSerializer(deserialize='_FilesConfig__deserialize')
class FilesConfig(Struct):
  pidfile = Field(str, default=None)
  stdout = Field(str, default=None)
  stderr = Field(str, default=None)

  @classmethod
  def deserialize(cls, context, node) -> 'FilesConfig':
    if not isinstance(node.value, str):
      raise NotImplementedError
    return cls.from_dir(node.value)

  @classmethod
  def from_dir(cls, dirpath: str) -> 'FilesConfig':
    return cls(
      os.path.join(dirpath, 'run', 'wsgi.pid'),
      os.path.join(dirpath, 'log', 'stdout.log'),
      os.path.join(dirpath, 'log', 'stderr.log'),
    )


class Status(enum.Enum):
  STOPPED = 0
  RUNNING = 1
  UNKNOWN = 2


@SerializeAs(UnionType.with_entrypoint_resolver('nr.utils.wsgi.runners.IWsgiRunner'))
class IWsgiRunner(Interface):

  def run(self, app_config: 'WsgiAppConfig', daemonize: bool = False) -> None:
    """
    Run the application as defined in *app_config*. If *daemonize* is set to `True`, the
    application must be run in the background, the function must immediately return and
    the current process must be able to exit without the application stopping.
    """

  @default
  def get_status(self, app_config: 'WsgiAppConfig') -> Status:
    """
    Returns the status of the application, i.e. whether it is currently running or not. This
    method is only relevant when the application was started in the background.
    """

    filename = app_config.files.pidfile
    if not filename:
      return Status.UNKNOWN
    return Pidfile(filename).get_status()

  @default
  def stop(self, app_config: 'WsgiAppConfig') -> None:
    """
    Stop the application if it is currently running in the background. This is a no-op if
    #get_status() does not return #Status.RUNNING.
    """

    filename = app_config.files.pidfile
    if not filename:
      return
    return Pidfile(filename).stop()


class WsgiAppConfig(Struct):
  """
  Basic app configuration that is bassed to a #IWsgiRunner to run an application.
  """

  entrypoint = Field(str)
  bind = Field(BindConfig, default=lambda: BindConfig('127.0.0.1', 8000))
  ssl = Field(SslConfig, default=None)
  files = Field(FilesConfig, default=lambda: FilesConfig.from_dir('./var'))
  runners = Field(dict(value_type=IWsgiRunner))

  @classmethod
  def load(self, filename: str, mapper: ObjectMapper = None) -> 'WsgiAppConfig':
    """
    Loads the #WsgiAppConfig from a YAML file specified with *filename*.
    """

    if not mapper:
      mapper = ObjectMapper(JsonModule())
    with open(filename) as fp:
      return mapper.deserialize(yaml.safe_load(fp), cls, filename=filename)

  def run(self, runner: str, daemonize: bool = False) -> None:
    self.runners[runner].run(self, daemonize)


# Utility

def is_reloader() -> bool:
  """
  Checks whether the current process is the reloader when using the #FlaskRunner.
  """

  if os.getenv('_FLASK_USE_RELOAER') == 'true' and not os.getenv('WERKZEUG_RUN_MAIN'):
    return True  # This is the Werkzeug reloader process

  return False


def is_main() -> bool:
  """
  Checks whether this is the main process, which can be the reloader thread in case
  the #FlaskRunner is used.
  """

  if os.getenv('_FLASK_USE_RELOAER') == 'true':
    return not os.getenv('WERKZEUG_RUN_MAIN')

  return True


def get_runner_class() -> Type[IWsgiRunner]:
  """
  Returns the runner class that is currently executing the application.
  """

  type_id = os.getenv('_WSGI_RUNNER_CLASS')
  if not type_id:
    raise EnvironmentError('No WSGI runner defined in environment.')
  cls = load_entrypoint(type_id)
  if not isinstance(cls, type) or not IWsgiRunner.implemented_by(cls):
    raise EnvironmentError('The defined WSGI runner class is invalid ({}).'.format(type_id))
  return cls


def load_entrypoint(ep: str) -> Any:
  """
  Loads an entrypoint definition of the form `<module>:<member>`.
  """

  module_name, member_name = ep.split(':', 1)
  return getattr(import_module(module_name), member_name)


def _type_id(obj: Any) -> str:
  if not isinstance(obj, type):
    obj = type(obj)
  return obj.__module__ + ':' + obj.__name__


class Pidfile:

  def __init__(self, filename: str) -> None:
    self.name = filename

  def set_pid(self, pid: int) -> None:
    """
    Writes the *pid* into the file.
    """

    with open(self.name) as fp:
      fp.write(str(pid))

  def get_pid(self) -> int:
    """
    Returns the PID saved in the file. May raise a #FileNotFounError if the file does not
    exist or a #ValueError if the file does not contain an integer.
    """

    with open(self.name) as fp:
      return int(fp.readline().strip())

  def get_status(self) -> Status:
    """
    Determines the #Status of a process.
    """

    try:
      pid = self.get_pid()
    except FileNotFoundError:
      return Status.STOPPED
    except ValueError:
      return Status.UNKNOWN
    if process_exists(pid):
      return Status.RUNNING
    return Status.STOPPED

  def stop(self) -> None:
    """
    Stops the process referenced by the PID file. If the file does not exist or the
    process is not alive, this is a no-op.
    """

    try:
      pid = self.get_pid()
    except (FileNotFoundError, ValueError):
      return
    process_terminate(pid)


# Runner implementations

@implements(IWsgiRunner)
class FlaskRunner(Struct):
  """
  Runs a #flask.Flask application using the Flask development server. This is not suitable
  for production, though very useful during development due to the built-in debugging
  capabilities.

  Note: Daemonizing the Flask runner is currently only available on systems that support
  #os.fork().
  """

  debug = Field(bool, default=False)  #: Enable the Flask server's debug capabilities.
  use_reloader = Field(bool, default=None)  #: Automatically defaults to `True` if #debug is enabled.
  redirect_stdio = Field(bool, default=False)  #: Enable stdio redirects.

  @override
  def run(self, app_config: WsgiAppConfig, daemonize: bool = False) -> None:
    import flask

    # Set up the environment.
    os.environ['_WSGI_RUNNER_CLASS'] = _type_id(self)
    use_reloader = self.debug if self.use_reloader is None else self.use_reloader
    if use_reloader:
      os.environ['_FLASK_USE_RELOAER'] = 'true'
    if self.debug:
      os.environ['FLASK_DEBUG'] = 'true'

    # Load the Flask application.
    app = load_entrypoint(app_config.entrypoint)
    if not isinstance(app, flask.Flask):
      raise RuntimeError('WsgiAppConfig.entrypoint ({}) must be a Flask application.'.format(app_config.entrypoint))

    # Setup stdio redirects.
    if self.redirect_stdio:
      stdout, stderr = self._init_redirects(app_config.files)
    else:
      stdout, stderr = None, None

    if app_config.files.pidfile:
      os.makedirs(os.path.dirname(app_config.files.pidfile), exist_ok=True)

    if app_config.ssl:
      ssl_context = (app_config.ssl.cert, app_config.ssl.key)
    else:
      ssl_context = None

    run = functools.partial(
      self._run,
      app=app,
      stdout=stdout,
      stderr=stderr,
      pidfile=app_config.files.pidfile,
      daemon=daemonize,
      host=app_config.bind.host,
      port=app_config.bind.port,
      debug=self.debug,
      use_reloader=use_reloader,
      ssl_context=ssl_context)

    if is_main() and self.get_status(app_config) == Status.RUNNING:
      raise RuntimeError('Application is already running.')

    if daemonize:
      spawn_daemon(run)
    else:
      run()

  def _init_redirects(self, files: FilesConfig) -> Tuple[Optional[TextIO], Optional[TextIO]]:
    if files.stdout:
      os.makedirs(os.path.dirname(files.stdout), exist_ok=True)
      stdout = open(files.stdout, 'a+')
    else:
      stdout = None

    if files.stderr and files.stderr != files.stdout:
      os.makedirs(os.path.dirname(files.stderr), exist_ok=True)
      stderr = open(files.stderr, 'a+')
    elif files.stderr == files.stdout:
      stderr = stdout
    else:
      stderr = None

    return stdout, stderr

  def _run(
    self,
    app: 'flask.Flask',
    stdout: Optional[TextIO],
    stderr: Optional[TextIO],
    pidfile: Optional[str],
    daemon: bool,
    host: str,
    port: int,
    debug: bool,
    use_reloader: bool,
    ssl_context: Tuple[str, str]
  ) -> None:
    """
    Internal function to actually invoke the Flask application after everything was prepared.
    """

    if stdout or stderr:
      replace_stdio(None, stdout, stderr)

    if pidfile:
      with open(pidfile, 'w') as fp:
        fp.write(str(os.getpid()))

    if daemon:
      logger.info('Process %s started.', os.getpid())

    try:
      app.run(
        host=host,
        port=port,
        debug=debug,
        use_reloader=use_reloader,
        ssl_context=ssl_context,
      )
    finally:
      if (not use_reloader or os.getenv('WERKZEUG_RUN_MAIN') == 'true') and pidfile:
        try:
          logger.info('Removing pidfile "%s" from PID %s.', pidfile, os.getpid())
          os.remove(pidfile)
        except OSError as exc:
          logger.exception('Unable to remove "%s".', pidfile)


@implements(IWsgiRunner)
class GunicornRunner(Struct):
  """
  Runs a WSGI application using [Gunicorn][0].

  [0]: https://gunicorn.org/
  """

  num_workers = Field(int, default=None)
  additional_options = Field([str], default=list)

  @override
  def run(self, app_config: WsgiAppConfig, daemonize: bool = False) -> None:
    command = [
      'gunicorn', app_config.entrypoint,
      '--bind', '{}:{}'.format(app_config.bind.host, app_config.bind.port)]
    if daemonize:
      command.append('--daemon')
    if app_config.files.pidfile:
      os.makedirs(os.path.dirname(app_config.files.pidfile), exist_ok=True)
      command += ['--pid', app_config.files.pidfile]
    if app_config.files.stdout:
      os.makedirs(os.path.dirname(app_config.files.stdout), exist_ok=True)
      command += ['--access-logfile', app_config.files.stdout]
    if app_config.files.stderr:
      os.makedirs(os.path.dirname(app_config.files.stderr), exist_ok=True)
      command += ['--error-logfile', app_config.files.stderr]
    if app_config.ssl:
      command += ['--certfile', app_config.ssl.cert, '--keyfile', app_config.ssl.key]
    if self.num_workers:
      command += ['--workers', str(self.num_workers)]
    command += self.additional_options
    env = os.environ.copy()
    env['_WSGI_RUNNER_CLASS'] = _type_id(self)
    subprocess.call(command, env=env)
