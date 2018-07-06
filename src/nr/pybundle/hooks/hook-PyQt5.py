
import os

def examine(finder, module, result):
  if module.name == 'PyQt5':
    result.imports.append('sip')
    result.modules += finder.iter_package_modules(module)  # TODO: Only the modules that are actually used?
    module.zippable = False
    module.package_data.append('Qt')  # TODO: Exclude libraries, plugins, qml, resources and translations if they are unused

    bin_dir = os.path.join(module.directory, 'Qt', 'bin')
    module.native_deps_path.append(bin_dir)
    for name in os.listdir(bin_dir):
      module.native_deps_exclude.append(os.path.join(bin_dir, name))
