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
import functools
import hashlib
import logging
import io
import json
import nr.fs
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from ._base import Dependency

logger = logging.getLogger(__name__)
CACHE_DIR = os.path.join(appdirs.user_cache_dir(__name__))


@functools.lru_cache()
def _get_dependencies_tool():
  """
  Checks if `Dependencies.exe` is in the system PATH. If not, it will be
  downloaded from GitHub to a temporary directory. The download will not
  be deleted afterwards as it may be used again later.

  Returns the path to `Dependencies.exe`.
  """

  for dirname in os.getenv('PATH', '').split(os.pathsep):
    filename = os.path.join(dirname, 'Dependencies.exe')
    if os.path.isfile(filename):
      logger.info('Dependencies Tool found at "{}"'.format(filename))
      return filename

  arch = 'x64' if sys.maxsize > 2**32 else 'x86'
  temp_dir = os.path.join(CACHE_DIR, 'Dependencies_' + arch)
  temp_exe = os.path.join(temp_dir, 'Dependencies.exe')
  url = 'https://github.com/lucasg/Dependencies/releases/download/v1.8/Dependencies_{}_Release.zip'.format(arch)

  if os.path.isfile(temp_exe):
    logger.info('Dependencies Tool found at "{}"'.format(temp_exe))
    return temp_exe

  logger.info('Dependencies Tool not found. Downloading ...')
  with urlopen(url) as fp:
    data = fp.read()

  logger.info('Extracting Dependencies Tool to "{}"'.format(temp_dir))
  with zipfile.ZipFile(io.BytesIO(data)) as zipf:
    nr.fs.makedirs(temp_dir)
    zipf.extractall(temp_dir)

  if not os.path.isfile(temp_exe):
    raise RuntimeError('"{}" does not exist after extraction'.format(temp_exe))

  return temp_exe


@functools.lru_cache()
def _get_known_dlls():
  """
  Returns a list of the known DLLs as reported by the Dependencies tool.
  """

  command = [_get_dependencies_tool(), '-json', '-knowndll']
  data = json.loads(subprocess.check_output(command))
  return list(set(data['x64'] + data['x86']))


def get_dependencies(pefile):
  """
  Returns a list of the Windows DLL names that the specified *pefile* imports.
  This list is non-recursive, thus containing only the directly imported DLL
  names.
  """

  # Check if we already analyzed this file before.
  hasher = hashlib.sha1(os.path.normpath(pefile).encode('utf8'))
  cachefile = hasher.hexdigest() + '_' + os.path.basename(pefile) + '-deps.json'
  cachefile = os.path.join(CACHE_DIR, cachefile)

  if nr.fs.compare_timestamp(pefile, cachefile):
    # Cachefile doesn't exist or is older than changes to pefile.
    logger.info('Analyzing "{}" ...'.format(pefile))
    nr.fs.makedirs(os.path.dirname(cachefile))

    command = [_get_dependencies_tool(), '-json', '-imports', pefile]
    logger.debug('Running command: {}'.format(command))
    with open(cachefile, 'wb') as fp:
      subprocess.check_call(command, stdout=fp, stderr=sys.stderr)
  else:
    logger.info('Using cached dependency information for "{}"'.format(pefile))

  with io.open(cachefile) as src:
    data = json.load(src)

  result = []
  knowns = [x.lower() for x in _get_known_dlls()]
  for module in data['Imports']:
    if module['Name'].lower() in knowns:
      continue
    result.append(Dependency(module['Name']))

  return result


def resolve_dependency(dep):
  """
  Attempts to find the #Dependency on the system. Returns the filename of the
  native library or None if it can not be found.
  """

  for dirname in os.getenv('PATH', '').split(os.pathsep):
    filename = os.path.join(dirname, dep.name)
    if os.path.isfile(filename):
      return nr.fs.get_long_path_name(filename)
  return None
