
def examine(finder, module, result):
  if module.name == 'six.moves': return
  assert module.name.startswith('six.moves.'), data
  try:
    module = __import__(module.name, fromlist=[None])
  except ImportError as exc:
    pass
  else:
    result.imports.append(module.__name__)
