
def extend_imports(module):
  if module.name.startswith('pkg_resources.extern.'):
    module.imports.append(module.name.replace('pkg_resources.extern', 'pkg_resources._vendor'))
