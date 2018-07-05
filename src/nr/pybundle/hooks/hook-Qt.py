
import Qt
import logging

logger = logging.getLogger(__name__)

def examine(finder, module, result):
  result.imports.append('Qt')
  result.imports.append(Qt.__binding__)
  # TODO: Import the whole binding's package, not just the root module.
  #result.imports += data.finder.iter_package_modules(module)
