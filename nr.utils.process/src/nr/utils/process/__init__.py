# -*- coding: utf8 -*-
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

import errno
import os
import signal
import sys
import time

__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
__version__ = '0.0.5'


def process_exists(pid):  # type: (int) -> bool
  """ Checks if the processed with the given *pid* exists. Returns #True if
  that is the case, #False otherwise. """

  if pid == 0:
    return False
  try:
    os.kill(pid, 0)
  except OSError as exc:
    if exc.errno == errno.ESRCH:
      return False
  return True


def process_terminate(pid, allow_kill: bool = True, timeout: int = 10) -> bool:
  """ Terminates the process with the given *pid*. First sends #signal.SIGINT,
  followed by #signal.SIGTERM after *timeout* seconds, followed by
  #signal.SIGKILL after *timeout* seconds if the process has not responded to
  the terminate signal.

  The fallback to kill can be disabled by setting *allow_kill* to False.
  Returns True if the process was successfully terminated or killed, or if
  the process did not exist in the first place. """

  get_time = getattr(time, 'perf_counter', None) or time.clock

  def _wait(timeout):
    tstart = get_time()
    while (get_time() - tstart) < timeout:
      if not process_exists(pid):
        return True
      time.sleep(0.1)
    return False

  try:
    os.kill(pid, signal.SIGINT)
    if _wait(timeout):
      return True
    os.kill(pid, signal.SIGTERM)
    if _wait(timeout):
      return True
    if allow_kill:
      os.kill(pid, signal.SIGKILL)
      return _wait(timeout)
    return False
  except OSError as exc:
    if exc.errno == errno.ESRCH:
      return True
    raise


def getpwgrnam(user, group):
  # type: (Optional[str], Optional[str]) -> (Optional[str], Optional[int], Optional[int])
  """ A combination of #pwd.getpwnam() and #pwd.getgrnam(), where *group*,
  if specified, overrides the group ID of the *user*. Returns a tuple of
  the user's home folder, the user ID and the group ID. """

  home, uid, gid = None, None, None
  if user:
    record = pwd.getpwnam(self.user)
    home, uid, gid = record.pw_dir, record.pw_uid, record.pw_gid
  if group:
    record = grp.getgrnam(self.group)
    gid = record.gr_gid
  return home, uid, gid


def replace_stdio(stdin=None, stdout=None, stderr=None):
  # type: (Optional[file], Optional[file], Optional[file])
  """ Replaces the file handles of stdin/sdout/stderr, closing the original
  file descriptors if necessary. """

  if stdin:
    os.dup2(stdin.fileno(), sys.stdin.fileno())
  if stdout:
    os.dup2(stdout.fileno(), sys.stdout.fileno())
  if stderr:
    os.dup2(stderr.fileno(), sys.stderr.fileno())


def detach():
  """ Detaches the current process from the parent process. This function
  requires #os.setsid() and thus works only on Unix systems. """

  os.setsid()


def spawn_fork(func, detach=True):
  """ Spawns a single fork process and calls *func*. If *detach* is #True,
  the fork will be detached first (note that this process will still be killed
  by it's parent process if it doesn't exist gracefully).

  This is useful if *func* spawns another process, which will then behave like
  a daemon (as it will NOT be killed if the original process dies). """

  if not callable(func):
    raise TypeError('func is of type {} which is not callable'.format(
      type(func).__name__))

  pid = os.fork()
  if pid > 0:
    # Return to the original caller
    return
  if detach:
    os.setsid()
  func()
  os._exit(os.EX_OK)


def spawn_daemon(func):
  """ Spawns a daemon process that runs *func*. This performs two forks to
  avoid the parent process killing the process that runs *func*.

  Note that this is only needed if you want to run a Python function as a
  daemon. If you were to spawn another process that should act as a daemon,
  you only need to fork once as the subprocess will then be the second "fork".
  """

  # TODO (@NiklasRosenstein): It would be great if the second fork could
  #   somehow report it's process ID to the original caller.

  if not callable(func):
    raise TypeError('func is of type {} which is not callable'.format(
      type(func).__name__))

  pid = os.fork()
  if pid > 0:
    # Return to the original caller.
    return
  os.setsid()
  pid = os.fork()
  if pid > 0:
    # Exit from second parent
    os._exit(os.EX_OK)
  func()
  os._exit(os.EX_OK)
