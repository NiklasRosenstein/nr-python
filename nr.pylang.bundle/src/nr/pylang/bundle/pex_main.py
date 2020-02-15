
import atexit
import datetime
import errno
import json
import logging
import os
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
        return False
      member = member[len(prefix):]
      for module in pex_info['unzip_modules']:
        module = module.replace('.', '/') + '/'
        if member.startswith(module):
          return True
      return False

    for member in zipf.namelist():
      if _check_unpack(member):
        target_dir = member.rpartition('/')[0].replace('/', os.path.sep)
        logger.debug('Unpacking "%s" to "%s"', member, target_dir)
        zipf.extract(member, os.path.join(tempdir, target_dir))

    sys.path.insert(0, tempdir)

    interactive = False
    if os.getenv('PEX_INTERACTIVE'):
      logger.debug('PEX_INTERACTIVE is set, entering interactive shell.')
      interactive = True
    elif not pex_info['entrypoint']:
      logger.debug('No entrypoint defined, entering interactive shell.')
      interactive = True

    if interactive:
      import code
      code.interact()
    else:
      logger.debug('Running entrypoint "%s"', pex_info['entrypoint'])
      filename = os.path.join(pex_file, pex_info['entrypoint'])
      code = compile(zipf.open(pex_info['entrypoint']).read().decode(), filename, 'exec')
      scope = {'__file__': pex_info, '__name__': '__main__'}
      exec(code, scope, scope)  # TODO: Python 2 compat


if __name__ == '__main__':
  main()
