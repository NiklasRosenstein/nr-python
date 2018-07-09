
from nr.pybundle.utils import pysubcmd

BINDING = pysubcmd.execute('''
  import Qt
  return Qt.__binding__
''')


def examine(finder, module, result):
  if module.name != 'Qt': return
  result.imports.append('Qt')
  result.imports.append(BINDING)
  for other in ['PyQt4', 'PyQt5', 'PySide2', 'PySide']:
    if other != BINDING:
      result.excludes.append(other)


def finalize(finder):
  # Make sure the imports for the used Qt components appear as
  # "naturally imported".
  for mod in list(finder.modules.values()):
    if mod.name.startswith('Qt.Qt'):
      submodule = BINDING + '.' + mod.name[3:]
      finder.find_module(submodule)
