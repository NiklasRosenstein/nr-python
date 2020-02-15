
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

logger = logging.getLogger('pex_main')


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


def main():
  init_logging()

  pex_file = get_pex_filename()
  logger.debug('PEX file is located at "%s"', pex_file)

  # We're okay with keeping the file open for the entire lifetime of the program.
  zipf = zipfile.ZipFile(pex_file)
  pex_info = json.loads(zipf.open('PEX-INFO').read().decode('utf8'))
  logger.debug('PEX info loaded: %r', pex_info)

  if pex_info['unzip_modules']:
    tempdir = os.path.join(
      os.path.expanduser(pex_info['root'] or '~/.pex'),
      os.path.basename(pex_file) + datetime.datetime.now().strftime('%Y%m%d%H%M'))
    logger.debug('Extracting modules %r to "%s"', pex_info['unzip_modules'], tempdir)
    makedirs(tempdir)
    atexit.register(lambda: [
      logger.debug('Deleting temporary directory "%s"', tempdir),
      shutil.rmtree(tempdir)])

    prefix = pex_info.get('lib', 'lib').rstrip('/') + '/'
    def _check_unpack(member):
      if not member.startswith(prefix):
        return None
      member = member[len(prefix):]
      for module in pex_info['unzip_modules']:
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

    sys.path.insert(0, tempdir)

    interactive = False
    if os.getenv('PEX_INTERACTIVE'):
      logger.debug('PEX_INTERACTIVE is set, enabling interactive mode.')
      interactive = True
    elif not pex_info['entrypoint']:
      interactive = True

    if interactive:
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
        return 0
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
        scope = {'__file__': pex_file, '__name__': '__main__'}
        eval(args.code, scope, scope)
        return 0
      elif args.args:
        with open(args.args[0]) as fp:
          compiled_code = compile(fp.read(), args.args[0], 'exec')
        scope = {'__file__': args.args[0], '__name__': '__main__'}
        exec(compiled_code, scope, scope)  # TODO: Python 2 compat
        return 0
      else:
        code.interact()
    else:
      logger.debug('Running entrypoint "%s"', pex_info['entrypoint'])
      filename = os.path.join(pex_file, pex_info['entrypoint'])
      compiled_code = compile(zipf.open(pex_info['entrypoint']).read().decode(), filename, 'exec')
      scope = {'__file__': pex_info, '__name__': '__main__'}
      exec(compiled_code, scope, scope)  # TODO: Python 2 compat
      return 0

  return 0


if __name__ == '__main__':
  sys.exit(main())
