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

import logging
import os
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


class ConfigReloaderTask(object):
  """
  A helper class to help reloading config files in the background.
  """

  def __init__(self, filename, load_config_function, logger=None):
    self.filename = filename
    self.load_config_function = load_config_function
    self._num_reloads = 0
    self._observer = None
    self._callbacks = []
    self._logger = logger or logging.getLogger('ConfigReloaderTask'.format(filename))
    self._value = None
    self._reload_lock = threading.Lock()
    self._data_lock = threading.Condition()

  def get(self):  # type: () -> Any
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
      raise RuntimeError('ConfigReloaderTask is already running.')
    self._logger.debug('filename=%r, starting reloader thread.', self.filename)
    self._observer = WatchdogFileObserver(self.filename, self._file_modified)
    self._observer.start()

  def stop(self):
    if self._observer:
      self._observer.stop()
      self._observer.join()
      self._observer = None

  def _file_modified(self, event):
    self._logger.debug('filename=%r, received file modified event.', self.filename)
    self.reload()


class WatchdogFileObserver(MaybeFileSystemEventHandler):

  def __init__(self, filename, callback):
    if watchdog is None:
      raise RuntimeError('watchdog module is not available')
    self.filename = os.path.normpath(os.path.abspath(filename))
    self.callback = callback
    self.observer = Observer()
    self.observer.schedule(self, path=os.path.dirname(self.filename), recursive=False)

  def start(self):
    self.observer.start()

  def stop(self):
    self.observer.stop()

  def join(self):
    self.observer.join()

  def on_modified(self, event):
    if event.src_path == self.filename:
      self.callback(event)
