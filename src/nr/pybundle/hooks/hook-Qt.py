
from nr.pybundle.utils import pysubcmd

BINDING = pysubcmd.execute('''
  import Qt
  return Qt.__binding__
''')

BINDIND_REQUIRES = {
  'PySide': ['shiboken'],
  'PySide2': ['shiboken2']
}.get(BINDING, [])


def module_found(module):
  if module.name != 'Qt': return
  module.imports.append(BINDING)
  for other in ['PyQt4', 'PyQt5', 'PySide2', 'PySide', 'shiboken', 'shiboken2']:
    if other == BINDING or other in BINDIND_REQUIRES: continue
    module.strip_imports(other)


def finalize(finder):
  # Make sure the imports for the used Qt components appear as
  # "naturally imported".
  for mod in list(finder.modules.values()):
    if mod.name.startswith('Qt.Qt'):
      submodule = BINDING + '.' + mod.name[3:]
      finder.find_module(submodule)
