
import Qt
import os

def examine(finder, module, result):
  if module.name != 'Qt': return
  result.imports.append('Qt')
  result.imports.append(Qt.__binding__)

  if Qt.__binding__ == 'PyQt5':
    # We imported the 'Qt' module, which in turn imported 'PyQt5'.
    # PyQt5 adds its bin/ directory the PATH, preventing proper
    # resolution of required DLLs later with nr.pybundle.
    import PyQt5
    paths = os.environ['PATH'].split(os.pathsep)
    paths.remove(os.path.dirname(PyQt5.__file__) + '\\Qt\\bin')
    os.environ['PATH'] = os.pathsep.join(paths)


def finalize(finder):
  for mod in list(finder.modules.values()):
    if mod.name.startswith('Qt.Qt'):
      submodule = Qt.__binding__ + '.' + mod.name[3:]
      finder.find_module(submodule)
