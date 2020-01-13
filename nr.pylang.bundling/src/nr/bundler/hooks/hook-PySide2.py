
from nr.pybundle import nativedeps
import os


def finalize(finder):
  whole_pyside = finder.hooks.options.get('PySide2:whole') == 'true'
  PySide2 = finder.find_module('PySide2')
  PySide2.package_data.append('plugins')
  for module in list(finder.modules.values()):
    if not module.name.startswith('PySide2.'): continue
    if module.type == module.NATIVE and module.natural:
      deps = nativedeps.Collection()
      deps.search_path = [PySide2.directory]
      deps.add(module.filename, recursive=True)
      for dep in deps:
        filename = os.path.join(PySide2.directory, dep.name)
        if os.path.isfile(filename) and dep.name not in PySide2.package_data:
          PySide2.package_data.append(dep.name)
    if not module.natural and not whole_pyside:
      del finder.modules[module.name]
  # TODO: if whole_pyside, even the designer.exe etc should be included.
