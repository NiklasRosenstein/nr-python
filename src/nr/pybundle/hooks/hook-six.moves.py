
from nr.pybundle.modules import ModuleInfo, HookResult

def examine(data):
  if data.module.name == 'six.moves': return HookResult([])
  assert data.module.name.startswith('six.moves.'), data
  try:
    module = __import__(data.module.name, fromlist=[None])
  except ImportError as exc:
    module = None
  def iter_modules():
    if module:
      yield ModuleInfo(
        module.__name__,
        module.__file__,
        data.finder.get_module_type(module.__file__),
        [data.module.name] + data.module.imported_from)
  return HookResult(iter_modules())
