
import six

def examine(finder, module, result):
  if module.name == 'six.moves': return
  assert module.name.startswith('six.moves.'), data
  name = module.name[10:]
  for move in six._moved_attributes:
    if isinstance(move, six.MovedModule) and move.name == name:
      result.imports.append(move.mod)
      module.treat_as_found = True
      break
