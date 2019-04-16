
import os
import sys

is_cygwin = sys.platform.startswith('cygwin')
is_msys = sys.platform.startswith('msys') or (not is_cygwin and os.sep == '/')  # mingw-...-python3 builds have sys.platform == win
is_win = is_msys or is_cygwin or sys.platform.startswith('win32')
is_purewin = os.name == 'nt' and os.sep == '\\'

is_linux = sys.platform.startswith('linux')
is_osx = sys.platform.startswith('darwin')
is_unix = is_msys or is_cygwin or is_linux or is_osx


def find_in_path(name, search_path=None, common_ext=True):
  """
  Finds the given file specified with *name* in the system's PATH, or in
  a custom *search_path*. With *common_ext* set to #True, the PATHEXT will
  be taken into account. It can also be a list of extensions to check.
  """

  if search_path is None:
    search_path = os.environ['PATH'].split(os.pathsep)
  if common_ext is True:
    common_ext = [''] + os.getenv('PATHEXT', '').split(os.pathsep)
  elif common_ext in (False, None):
    common_ext = ['']
  elif not isinstance(common_ext, (list, tuple)):
    common_ext = list(common_ext)
  for dirname in search_path:
    filename = os.path.join(dirname, name)
    for ext in common_ext:
      ext_fn = filename + ext
      if os.path.isfile(ext_fn):
        return ext_fn
  return None


def get_python_executables():
  """
  Returns a dictionary that maps the Python interpreter base name to its
  absolute filename. A second entry may contain the `pythonw` version that
  is for GUI applications.
  """

  dirname, name = os.path.split(sys.executable)

  if is_win:
    add_ext = '.exe'
    check_ext = ['.exe']
    if name.endswith('.exe'):
      name = name[:-4]
    if is_msys or is_cygwin:
      check_ext.append('')
  else:
    add_ext = ''
    check_ext = ['']

  result = {
    'python' + add_ext: sys.executable
  }

  # Check for the existens of pythonw.
  for path in [os.path.join(dirname, name + 'w'), os.path.join(dirname, name.replace('python', 'pythonw'))]:
    for ext in check_ext:
      pythonw = path + ext
      if os.path.isfile(pythonw):
        result['pythonw' + add_ext] = pythonw
        break
    else:
      continue
    break

  if len(result) == 1:
    pythonw = find_in_path(name + 'w', common_ext=check_ext)
    if not pythonw:
      pythonw = find_in_path(name.replace('python', 'pythonw'), common_ext=check_ext)
    if pythonw:
      result['pythonw' + add_ext] = pythonw

  return result
