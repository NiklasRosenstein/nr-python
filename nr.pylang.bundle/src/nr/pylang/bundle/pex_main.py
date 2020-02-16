
import argparse
import atexit
import code
import datetime
import errno
import inspect
import json
import logging
import os
import pkg_resources
import shutil
import sys
import zipfile

try: from importlib import reload
except ImportError: from imp import reload

logger = logging.getLogger('pex_main')


if sys.version_info[0] == 3:
  exec_ = getattr(__import__('builtins'), 'exec')
else:
  def exec_(_code_, _globs_=None, _locs_=None):
    """Execute code in a namespace."""
    if _globs_ is None:
        frame = sys._getframe(1)
        _globs_ = frame.f_globals
        if _locs_ is None:
            _locs_ = frame.f_locals
        del frame
    elif _locs_ is None:
        _locs_ = _globs_
    exec("""exec _code_ in _globs_, _locs_""")


def makedirs(path, exist_ok=True):
  try:
    os.makedirs(path)
  except OSError as exc:
    if exist_ok and exc.errno == errno.EEXIST:
      return
    raise


def init_logging():
  log_format = os.getenv('PEX_LOGFORMAT')
  verbosity = os.getenv('PEX_VERBOSE', '').strip().lower()
  if not verbosity and not log_format:
    return

  try: verbosity = int(verbosity)
  except ValueError: pass

  if verbosity and not log_format:
    log_format = '%(message)s'

  if not verbosity:
    level = logging.ERROR
  elif verbosity in (1, 'true'):
    level = logging.WARNING
  elif verbosity == 2:
    level = logging.INFO
  elif verbosity >= 3:
    level = logging.DEBUG

  logging.basicConfig(format=log_format, level=level)


def get_pex_filename():
  """ The code for this function is taken from the original PEX project. """

  pex_file = os.getenv('PEX_FILE')
  if pex_file:
    return pex_file

  __entry_point__ = None
  if '__file__' in globals() and __file__ is not None:
    __entry_point__ = os.path.dirname(__file__)
  elif '__loader__' in globals():
    from pkgutil import ImpLoader
    if hasattr(__loader__, 'archive'):
      __entry_point__ = __loader__.archive
    elif isinstance(__loader__, ImpLoader):
      __entry_point__ = os.path.dirname(__loader__.get_filename())

  if __entry_point__ is None:
    sys.stderr.write('Could not launch python executable!\n')
    sys.exit(2)

  sys.path[0] = os.path.abspath(sys.path[0])
  sys.path.insert(0, os.path.abspath(os.path.join(__entry_point__, 'lib')))

  return __entry_point__


def unzip_modules(zipf, prefix, modules, tempdir):
  logger.debug('Extracting modules %r to "%s"', modules, tempdir)

  def _check_unpack(member):
    if not member.startswith(prefix):
      return None
    member = member[len(prefix):]
    for module in modules:
      module = module.replace('.', '/') + '/'
      if member.startswith(module):
        return member
    return None

  for member in zipf.namelist():
    target_fn = _check_unpack(member)
    if target_fn:
      filename = os.path.join(tempdir, target_fn.replace('/', os.path.sep))
    elif member.endswith('.egg-info/entry_points.txt'):
      parent, basename = member.rpartition('/')[::2]
      filename = os.path.join(tempdir, parent.rpartition('/')[-1], basename)
    else:
      continue
    logger.debug('Unpacking "%s" to "%s"', member, filename)
    makedirs(os.path.dirname(filename))
    with zipf.open(member) as src:
      with open(filename, 'wb') as dst:
        shutil.copyfileobj(src, dst)


def run_interactive(pex_filename):
  parser = argparse.ArgumentParser()
  parser.add_argument('args', nargs='...')
  parser.add_argument('-l', '--list', action='store_true')
  parser.add_argument('-s', '--script')
  parser.add_argument('-c', metavar='EXPR')
  args = parser.parse_args()

  if args.list:
    if args.args:
      parser.error('unexpected additional arguments with --list')
    for ep in pkg_resources.iter_entry_points('console_scripts'):
      print(ep.name)
  elif args.script:
    ep = next((x for x in pkg_resources.iter_entry_points('console_scripts')
      if x.name == args.script), None)
    if not ep:
      parser.error('no entrypoint "{}" in console_scripts'.format(args.script))
    sys.argv[1:] = args.args
    entry_point = ep.load()
    if 'prog' in inspect.getfullargspec(entry_point).args:
      kwargs = {'prog': args.script}
    else:
      kwargs = {}
    return entry_point(**kwargs)
  elif args.c:
    sys.argv[1:] = args.args
    scope = {'__file__': pex_filename, '__name__': '__main__'}
    exec(args.c, scope, scope)
  elif args.args:
    with open(args.args[0]) as fp:
      compiled_code = compile(fp.read(), args.args[0], 'exec')
    scope = {'__file__': args.args[0], '__name__': '__main__'}
    exec_(compiled_code, scope, scope)
  else:
    code.interact()
  return 0


def run_entrypoint(zipf, entrypoint):
  logger.debug('Running entrypoint "%s"', pex_info['entrypoint'])
  filename = os.path.join(pex_file, pex_info['entrypoint'])
  compiled_code = compile(zipf.open(pex_info['entrypoint']).read().decode(), filename, 'exec')
  scope = {'__file__': pex_info, '__name__': '__main__'}
  exec_(compiled_code, scope, scope)
  return 0


def main():
  init_logging()

  pex_file = get_pex_filename()
  logger.debug('PEX file is located at "%s"', pex_file)

  # We're okay with keeping the file open for the entire lifetime of the program.
  zipf = zipfile.ZipFile(pex_file)
  pex_info = json.loads(zipf.open('PEX-INFO').read().decode('utf8'))
  logger.debug('PEX info loaded: %r', pex_info)

  tempdir = os.path.join(
    os.path.expanduser(pex_info['root'] or '~/.pex'),
    os.path.basename(pex_file) + datetime.datetime.now().strftime('%Y%m%d%H%M'))
  makedirs(tempdir)
  atexit.register(lambda: [
    logger.debug('Deleting temporary directory "%s"', tempdir),
    shutil.rmtree(tempdir)])

  prefix = pex_info.get('lib', 'lib').rstrip('/') + '/'
  sys.path.insert(0, os.path.join(pex_file, prefix))

  if pex_info['unzip_modules']:
    unzip_modules(zipf, prefix, pex_info['unzip_modules'], tempdir)
    sys.path.insert(0, tempdir)

  reload(pkg_resources)

  interactive = False
  if os.getenv('PEX_INTERACTIVE'):
    logger.debug('PEX_INTERACTIVE is set, enabling interactive mode.')
    interactive = True
  elif not pex_info['entrypoint']:
    interactive = True

  if interactive:
    return run_interactive(pex_file)
  else:
    return run_entrypoint(zipf, pex_info['entrypoint'])


if __name__ == '__main__':
  sys.exit(main())
