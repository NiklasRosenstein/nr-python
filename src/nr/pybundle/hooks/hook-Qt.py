
from nr.pybundle.utils import pysubcmd

BINDING = pysubcmd.execute('''
  import Qt
  return Qt.__binding__
''')

BINDIND_REQUIRES = {
  'PySide': ['shiboken'],
  'PySide2': ['shiboken2']
}.get(BINDING, [])


def inspect_module(module):
  if module.name == 'Qt':
    module.imports.append(BINDING)
    for other in ['PyQt4', 'PyQt5', 'PySide2', 'PySide', 'shiboken', 'shiboken2']:
      if other == BINDING or other in BINDIND_REQUIRES: continue
      module.strip_imports(other)
  elif module.name.startswith('Qt.'):
    module.imports.append(BINDING + module.name[2:])
