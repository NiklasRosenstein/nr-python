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

try:
  from urllib.request import urlopen
except ImportError:
  from urllib2 import urlopen

import appdirs
import csv
import ctypes
import hashlib
import logging
import io
import nr.path
import os
import shutil
import subprocess
import tempfile
import zipfile
from ._base import Dependency

logger = logging.getLogger(__name__)
CACHE_DIR = os.path.join(appdirs.user_cache_dir('python-bundler'), 'windll')


def _get_long_path_name(path):
  """
  Returns the long path name for a Windows path, i.e. the properly cased
  path of an existing file or directory.
  """

  # Thanks to http://stackoverflow.com/a/3694799/791713
  buf = ctypes.create_unicode_buffer(len(path) + 1)
  GetLongPathNameW = ctypes.windll.kernel32.GetLongPathNameW
  res = GetLongPathNameW(path, buf, len(path) + 1)
  if res == 0 or res > 260:
    return path
  else:
    return buf.value


def get_dependency_walker():
  """
  Checks if `depends.exe` is in the system PATH. If not, it will be downloaded
  and extracted to a temporary directory. Note that the file will not be
  deleted afterwards.

  Returns the path to the Dependency Walker executable.
  """

  for dirname in os.getenv('PATH', '').split(os.pathsep):
    filename = os.path.join(dirname, 'depends.exe')
    if os.path.isfile(filename):
      logger.info('Dependency Walker found at "{}"'.format(filename))
      return filename

  temp_exe = os.path.join(tempfile.gettempdir(), 'depends.exe')
  temp_dll = os.path.join(tempfile.gettempdir(), 'depends.dll')
  if os.path.isfile(temp_exe):
    logger.info('Dependency Walker found at "{}"'.format(temp_exe))
    return temp_exe

  logger.info('Dependency Walker not found. Downloading ...')
  with urlopen('http://dependencywalker.com/depends22_x64.zip') as fp:
    data = fp.read()

  logger.info('Extracting Dependency Walker to "{}"'.format(temp_exe))
  with zipfile.ZipFile(io.BytesIO(data)) as fp:
    with fp.open('depends.exe') as src:
      with open(temp_exe, 'wb') as dst:
        shutil.copyfileobj(src, dst)
    with fp.open('depends.dll') as src:
      with open(temp_dll, 'wb') as dst:
        shutil.copyfileobj(src, dst)

  return temp_exe


def get_dependencies(pefile):
  """
  Uses Dependency Walker to get a list of dependencies for the specified
  PE file (a Windows executable or dynamic link library).
  """

  # Check if we already analyzed this file before.
  hasher = hashlib.sha1(os.path.normpath(pefile).encode('utf8'))
  cachefile = hasher.hexdigest() + '_' + os.path.basename(pefile) + '-deps.csv'
  cachefile = os.path.join(CACHE_DIR, cachefile)

  if nr.path.compare_timestamp(pefile, cachefile):
    # Cachefile doesn't exist or is older than changes to pefile.
    logger.info('Analyzing "{}" ...'.format(pefile))
    nr.path.makedirs(os.path.dirname(cachefile))

    command = [get_dependency_walker(), '/c', '/oc:' + cachefile, pefile]
    logger.debug('Running command: {}'.format(command))
    code = subprocess.call(command)

    if code > 0x00010000:  # Processing error and no work was done
      raise RuntimeError('Dependency Walker exited with non-zero returncode {}.'.format(code))

  else:
    logger.info('Using cached dependency information for "{}"'.format(pefile))

  result = []
  with io.open(cachefile) as src:
    src.readline()  # header
    for line in csv.reader(src):
      dep = Dependency(line[1])
      if dep.name.lower()[:6] in ('api-ms', 'ext-ms'):
        continue
      result.append(dep)

  return result


def resolve_dependency(dep):
  """
  Attempts to find the #Dependency on the system. Returns the filename of the
  native library or None if it can not be found.
  """

  for dirname in os.getenv('PATH', '').split(os.pathsep):
    filename = os.path.join(dirname, dep.name)
    if os.path.isfile(filename):
      return _get_long_path_name(filename)
  return None
