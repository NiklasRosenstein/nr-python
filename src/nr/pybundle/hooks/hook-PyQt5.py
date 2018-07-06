
def examine(finder, module, result):
  if module.name == 'PyQt5':
    result.imports.append('sip')
    result.modules += finder.iter_package_modules(module)
    module.zippable = False
    module.package_data.append('Qt')
  module.do_native_deps = False  # included in package_data
