
import sys
import nr.types
from .utils import system


class BundleConfig(nr.types.Named):
  __annotations__ = [
    ('lib_dir', str),
    ('lib_dynload_dir', str)
  ]


if system.is_unix:
  conf = BundleConfig(
    'lib/python{}'.format(sys.version[:3]),
    'lib/python{}/lib-dynload'.format(sys.version[:3])
  )
else:
  conf = BundleConfig(
    'lib',
    'lib'
  )
