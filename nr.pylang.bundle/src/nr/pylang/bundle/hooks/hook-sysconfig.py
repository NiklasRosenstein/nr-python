
import os


def extend_imports(module):
  if module.name == 'sysconfig' and os.name == 'posix':
    import sysconfig
    if hasattr(sysconfig, '_get_sysconfigdata_name'):
      module.imports.append(sysconfig._get_sysconfigdata_name(True))
    else:
      module.imports.append('_sysconfigdata')
