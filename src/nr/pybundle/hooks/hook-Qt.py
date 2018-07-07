
import Qt
import logging

logger = logging.getLogger(__name__)

def examine(finder, module, result):
  result.imports.append('Qt')
  result.imports.append(Qt.__binding__)
  # TODO: Import the whole binding's package, not just the root module.
  #result.imports += data.finder.iter_package_modules(module)


def finalize(finder):
  for mod in list(finder.modules.values()):
    if mod.name.startswith('Qt.Qt'):
      submodule = Qt.__binding__ + '.' + mod.name[3:]
      finder.find_module(submodule)
