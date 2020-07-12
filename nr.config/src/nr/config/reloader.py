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

from typing import Any, Callable, Optional, Type
import logging
import os
import time
import threading
import sys

try:
  import watchdog
except ImportError:
  watchdog = None
  MaybeFileSystemEventHandler = object
else:
  from watchdog.observers import Observer
  from watchdog.events import FileSystemEventHandler as MaybeFileSystemEventHandler

LoadConfigFunc = Callable[[str], Any]


class BaseObserver:

  def __init__(self, filename: str, callback: Callable[[], Any]) -> None:
    self.filename = os.path.normpath(os.path.abspath(filename))
    self.callback = callback

  def start(self):
    raise NotImplementedError

  def stop(self):
    raise NotImplementedError

  def join(self):
    raise NotImplementedError


class WatchdogFileObserver(BaseObserver, MaybeFileSystemEventHandler):

  def __init__(self, filename: str, callback: Callable[[], Any]):
    if watchdog is None:
      raise RuntimeError('watchdog module is not available')
    MaybeFileSystemEventHandler.__init__(self)
    BaseObserver.__init__(self, os.path.normpath(os.path.abspath(filename)), callback)
    self._observer = Observer()
    self._observer.schedule(self, path=os.path.dirname(self.filename), recursive=False)

  def start(self):
    self._observer.start()

  def stop(self):
    self._observer.stop()

  def join(self):
    self._observer.join()

  def on_modified(self, event):
    if event.src_path == self.filename:
      self.callback()


class PollingFileObserver(BaseObserver):

  def __init__(self, filename: str, callback: Callable[[], Any], poll_interval: float = 2):
    super().__init__(filename, callback)
    self.poll_interval = poll_interval
    self._thread = None
    self._stopped = False

  def start(self):
    if self._thread is not None:
      raise RuntimeError('already started')
    self._stopped = False
    self._thread = threading.Thread(target=self._run)
    self._thread.daemon = True
    self._thread.start()

  def stop(self):
    self._stopped = True

  def join(self):
    self._thread.join()

  def _get_time(self) -> Optional[float]:
    try:
      return os.path.getmtime(self.filename)
    except FileNotFoundError:
      return None

  def _run(self):
    mtime = self._get_time()
    while not self._stopped:
      time.sleep(self.poll_interval)
      new_mtime = self._get_time()
      if mtime != new_mtime:
        try:
          self.callback()
        except:
          logger.exception('PollingFileObserver: error in callback')
        mtime = new_mtime


class ReloadTask:
  """
  A helper class to help reloading config files in the background.
  """

  LOGGER = logging.getLogger(__name__ + '.ReloadTask')

  def __init__(
    self,
    filename: str,
    load_config_function: LoadConfigFunc,
    logger: logging.Logger = None,
    observer_class: Type = None,
  ) -> None:
    if observer_class is None:
      if watchdog is not None:
        observer_class = WatchdogFileObserver
      else:
        logger.info('"watchdog" module is not available, falling back to PollingFileObserver')
        observer_class = PollingFileObserver
    self.filename = filename
    self.load_config_function = load_config_function
    self.observer_class = observer_class
    self._num_reloads = 0
    self._observer = None
    self._callbacks = []
    self._logger = logger or self.LOGGER
    self._value = None
    self._reload_lock = threading.Lock()
    self._data_lock = threading.Condition()

  def get(self) -> Any:
    """
    Returns the currently loaded configuration. If the configuration was never
    loaded, it will be loaded for the first time. Note that this can return None
    if the config could not be loaded.
    """

    with self._data_lock:
      if self._num_reloads > 0:
        return self._value
    return self.reload()

  def reload(self):
    """
    Reloads the configuration. Two concurrent calls of this method will result
    in one thread waiting for the other to finish and only one actual reload
    to occur. Sequential calls will result in multiple actual reloads.
    """

    # If another call to reload() is currently in progress, we wait until that
    # is finished and we can retrieve the new configuration value.
    if self._reload_lock.locked():
      self._logger.debug('filename=%r, reloading already in progress...', self.filename)
      with self._data_lock:
        self._data_lock.wait()
        return self._value

    # Indicate that a reload is in progress.
    with self._reload_lock:
      try:
        config = self.load_config_function(self.filename)
      except:
        self._logger.exception('filename=%r, error during reload.', self.filename)
        with self._data_lock:
          self._data_lock.notify_all()
      else:
        with self._data_lock:
          self._num_reloads += 1
          self._value = config
          # Notify all other calls stuck in reload() waiting for this one to finish
          # that the new value can be read.
          self._data_lock.notify_all()

        # Invoke callbacks for the changed config.
        for callback in self._callbacks:
          try:
            callback(config)
          except:
            self._logger.exception('filename=%r, error during callback %r.', self.filename, callback)

        return config

  def reload_callback(self, callback):
    """
    Registers a callback that is invoked when the config was reloaded. The new
    configuration will be passed as sole argument to the callback.
    """

    self._callbacks.append(callback)

  def start(self):
    if self._observer:  # TODO: Check if the observer is running.
      raise RuntimeError('ReloadTask is already running.')
    self._logger.debug('filename=%r, starting reloader thread.', self.filename)
    self._observer = self.observer_class(self.filename, self._file_modified)
    self._observer.start()

  def stop(self):
    if self._observer:
      self._observer.stop()
      self._observer.join()
      self._observer = None

  def _file_modified(self):
    self._logger.debug('filename=%r, received file modified event.', self.filename)
    self.reload()
