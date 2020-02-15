
def inspect_module(module):
  if module.name == 'certifi':
    module.is_zippable = False
    module.package_data = ['cacert.pem']
