
import os

try:
  from inspect import getfullargspec as getargspec
except ImportError:
  from inspect import getargspec


def extend_imports(module):
  if module.name == 'sysconfig' and os.name == 'posix':
    import sysconfig
    if hasattr(sysconfig, '_get_sysconfigdata_name'):
      args = []
      if getargspec(sysconfig._get_sysconfigdata_name).args:
        args = [True]
      sysconfig_name = sysconfig._get_sysconfigdata_name(*args)
    else:
      sysconfig_name = '_sysconfigdata'
    module.imports.append(sysconfig_name)
