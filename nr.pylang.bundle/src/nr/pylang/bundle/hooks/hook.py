
import pkg_resources
import warnings


def _find_distribution_for_module(module_name, _cache={}):  # TODO: Performance bottleneck
  """ Attempts to find a #pkg_resources.Distribution for a module. This
  is done by checking if any of the distributions provide the module
  filename. """

  if module_name in _cache:
    return _cache[module_name]

  root = module_name.partition('.')[0]
  results = []
  for dist in pkg_resources.working_set:
    if not dist.has_metadata('top_level.txt'):
      continue
    top_level = dist.get_metadata('top_level.txt').split('\n')
    if root in top_level:
      results.append(dist)

  variants = [
    '/'.join(module_name.split('.')) + '.py',
    '/'.join(module_name.split('.') + ['__init__.py'])
  ]

  finalists = []
  for dist in results:
    if dist.has_metadata('RECORD'):
      record = dist.get_metadata('RECORD').split('\n')
    elif dist.has_metadata('SOURCES.txt'):
      record = dist.get_metadata('SOURCES.txt').split('\n')
    else:
      continue
    for x in record:
      if any(y in x for y in variants):
        finalists.append(dist)
        break

  if len(finalists) > 1:
    warnings.warn('found multiple distributions providing "{}": {}'
      .format(module_name, finalists), UserWarning)
    result = None
  else:
    result = next(iter(finalists), None)

  _cache[module_name] = result
  return result


def _get_module_breadcrumbs(module):
  result = []
  while module:
    result.append(module)
    module = module.parent
  result.reverse()
  return result


# This is hook is invoked for every module (even the ones not found).

def inspect_module(module):
  assert module.graph, ('Module.graph is None for {!r}'.format(module.name), module.parent)

  # Find entry_points.txt for the parent module that is not a namespace
  # package and for which we can find a distribution.
  for item in _get_module_breadcrumbs(module):
    if item.is_namespace_pkg(): continue
    if item.entry_points is not None: break
    dist = _find_distribution_for_module(module.name)
    if dist and dist.has_metadata('entry_points.txt'):
      item.entry_points = dist.get_metadata('entry_points.txt')
      break


def collect_data(module, bundle):
  if module.is_pkg() and not hook.has_handler(module.name):
    # Include all package data by default.
    module.package_data.append('.')
    module.package_data_ignore.append('*.pyc')
    module.package_data_ignore.append('*.py')
