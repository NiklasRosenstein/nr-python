
# This is hook is invoked for every module (even the ones not found).

def collect_data(module, bundle):
  if module.is_pkg() and not hook.has_handler(module.name):
    # Include all package data by default.
    module.package_data.append('.')
    module.package_data_ignore.append('*.pyc')
    module.package_data_ignore.append('*.py')
