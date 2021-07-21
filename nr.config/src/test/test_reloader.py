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

from nr.config.reloader import ReloadTask, WatchdogFileObserver, PollingFileObserver
import os
import nr.fs
import time
import threading


def _test_reload_task(observer_class):
  import logging
  logging.info('_test_reload_task START')
  event = threading.Event()
  with nr.fs.tempfile(suffix='_test_reload_task') as fp:
    logging.info('Tempfile created: %s', fp.name)
    fp.close()
    logging.info('Tempfile closed: %s', fp.name)
    import time; time.sleep(0.4)
    try:
      task = ReloadTask(fp.name, lambda fn: event.set(), observer_class=observer_class)
      task.start()
      time.sleep(0.1)
      assert not event.is_set()
      mtime = os.path.getmtime(fp.name)
      logging.info('Reopening file')
      temp_fp = open(fp.name, 'w')
      temp_fp.write('test')
      temp_fp.close()
      logging.info('Closing file')
      assert os.path.getmtime(fp.name) != mtime
      event.wait(2)
      assert event.is_set(), 'file change not detected'
    finally:
      task.stop()


def test_watchdog_file_observer():
  _test_reload_task(WatchdogFileObserver)


def test_polling_file_observer():
  _test_reload_task(lambda f, c: PollingFileObserver(f, c, poll_interval=0.1))
