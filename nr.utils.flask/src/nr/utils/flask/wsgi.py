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

from importlib import import_module
from nr.databind.core import CollectionType, Field, SerializeAs, Struct, UnionType
from nr.utils.process import process_exists, process_terminate, replace_stdio, spawn_daemon
import enum
import logging
import os
import subprocess

logger = logging.getLogger(__name__)
_WsgiRunnerType = UnionType({})
STDOUT = '<stdout>'


def is_live():
  if os.getenv('NR_UTILS_FLASK_USE_RELOADER') == 'true' and not os.getenv('WERKZEUG_RUN_MAIN'):
    return False  # This is the Werkzeug reloader process
  return True


def get_runner_name():
  return os.getenv('NR_UTILS_FLASK_RUNNER')


class Status(enum.Enum):
  STOPPED = 0
  RUNNING = 1
  UNKNOWN = 2


@SerializeAs(_WsgiRunnerType)
class WsgiRunner(Struct):
  entrypoint = Field(str)
  host = Field(str, default='127.0.0.1')
  port = Field(int, default=8000)
  pidfile = Field(str, default=None)
  stdout = Field(str, default=None)
  stderr = Field(str, default=None)  #: Can be special value "<stdout>".

  def start(self, daemonize: bool = False) -> None:
    raise NotImplementedError(type(self).__name__)

  def status(self) -> Status:
    if not self.pidfile:
      return Status.UNKNOWN
    try:
      pid = self._get_pid()
    except FileNotFoundError:
      return Status.STOPPED
    except ValueError:
      return Status.UNKNOWN
    if process_exists(pid):
      return Status.RUNNING
    return STATUS.STOPPED

  def stop(self) -> None:
    try:
      pid = self._get_pid()
    except (FileNotFoundError, ValueError):
      return
    process_terminate(pid)

  def _get_pid(self) -> int:
    with open(self.pidfile) as fp:
      return int(fp.readline().strip())


class GunicornWsgiRunner(WsgiRunner):

  def start(self, daemonize: bool = False) -> None:
    command = ['gunicorn', self.entrypoint, '--bind', '{}:{}'.format(self.host, self.port)]
    if daemonize:
      command.append('--daemon')
    if self.pidfile:
      os.makedirs(os.path.dirname(self.pidfile), exist_ok=True)
      command += ['--pid', self.pidfile]
    if self.stdout:
      os.makedirs(os.path.dirname(self.stdout), exist_ok=True)
      command += ['--access-logfile', self.stdout]
    if self.stderr:
      os.makedirs(os.path.dirname(self.stderr), exist_ok=True)
      command += ['--error-logfile', self.stderr]
    env = os.environ.copy()
    env['NR_UTILS_FLASK_RUNNER'] = 'gunicorn'
    subprocess.call(command)


class FlaskAppRunner(WsgiRunner):
  debug = Field(bool, default=False)
  use_reloader = Field(bool, default=None)
  ssl_context = Field(CollectionType(str, py_type=tuple), default=None)

  def start(self, daemonize: bool = False) -> None:
    use_reloader = self.debug if self.use_reloader is None else self.use_reloader
    if use_reloader:
      os.environ['NR_UTILS_FLASK_USE_RELOADER'] = 'true'
    os.environ['NR_UTILS_FLASK_RUNNER'] = 'flask'

    import flask
    module_name, member_name = self.entrypoint.split(':')
    app = getattr(import_module(module_name), member_name)
    if not isinstance(app, flask.Flask):
      raise RuntimeError('entrypoint {!r} must be a Flask application.'.format(self.entrypoint))

    if self.stdout:
      os.makedirs(os.path.dirname(self.stdout), exist_ok=True)
      stdout = open(self.stdout, 'a+')
    else:
      stdout = None

    if self.stderr and self.stderr != self.stdout:
      os.makedirs(os.path.dirname(self.stderr), exist_ok=True)
      stderr = open(self.stderr, 'a+')
    elif self.stderr == self.stdout:
      stderr = stdout
    else:
      stderr = None

    if self.pidfile:
      os.makedirs(os.path.dirname(self.pidfile), exist_ok=True)

    def run():
      if stdout or stderr:
        replace_stdio(None, stdout, stderr)
      if self.pidfile:
        with open(self.pidfile, 'w') as fp:
          fp.write(str(os.getpid()))
      if daemonize:
        logger.info('Process %s started.', os.getpid())
      try:
        app.run(
          host=self.host,
          port=self.port,
          debug=self.debug,
          use_reloader=use_reloader,
          ssl_context=self.ssl_context,
        )
      finally:
        if (not use_reloader or os.getenv('WERKZEUG_RUN_MAIN') == 'true') and self.pidfile:
          try:
            logger.info('Removing pidfile "%s" from PID %s.', self.pidfile, os.getpid())
            os.remove(self.pidfile)
          except OSError as exc:
            logger.exception('Unable to remove "%s".', self.pidfile)

    if daemonize:
      spawn_daemon(run)
    else:
      run()


_WsgiRunnerType.type_resolver.register_union_member('gunicorn', GunicornWsgiRunner)
_WsgiRunnerType.type_resolver.register_union_member('flask', FlaskAppRunner)
