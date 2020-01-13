
import six

def inspect_module(module):
  if not module.name.startswith('six.moves.'):
    return

  module.load_imports()
  name = module.name[10:]
  for move in six._moved_attributes:
    if isinstance(move, six.MovedModule) and move.name == name:
      module.imports.append(move.mod)
