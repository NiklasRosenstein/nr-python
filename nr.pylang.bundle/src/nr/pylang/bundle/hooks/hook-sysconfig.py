
import os


def extend_imports(module):
  if module.name == 'sysconfig' and os.name == 'posix':
    import sysconfig
    module.imports.append(sysconfig._get_sysconfigdata_name(True))
