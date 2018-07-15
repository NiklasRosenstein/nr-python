
import os
import shutil
from nr.pybundle.nativedeps import Dependency
from nr.pybundle.utils import pysubcmd, system
from nr.pybundle.utils.fs import copy_files_checked


typelib_data = {}
module_versions = {}


def _get_typelib_info(module, version):
  if version is None and module in module_versions:
    version = module_versions[module]
  elif version is not None and module not in module_versions:
    module_versions[module] = version
  if (module, version) in typelib_data:
    return typelib_data[(module, version)]

  statement = """
    import gi
    gi.require_version("GIRepository", "2.0")
    from gi.repository import GIRepository
    repo = GIRepository.Repository.get_default()
    module, version = (%r, %r)
    repo.require(module, version, GIRepository.RepositoryLoadFlags.IREPOSITORY_LOAD_FLAG_LAZY)
    return {
      'sharedlib': repo.get_shared_library(module),
      'typelib': repo.get_typelib_path(module),
      'deps': repo.get_immediate_dependencies(module) or []
    }
  """ % (module, version)

  info = pysubcmd.execute(statement)
  data = {
    'name': module,
    'version': version,
    'libs': [x for x in info['sharedlib'].split(',') if x],
    'typelib': info['typelib'],
    'deps': info['deps']
  }
  typelib_data[(module, version)] = data
  return data


def collect_data(module, bundle):
  if module.graph['gi.repository'].type == module.NOTFOUND: return
  repo_name = module.name[len('gi.repository.'):]
  if not repo_name: return
  if repo_name != 'GIRepository':
    module.graph.collect_modules('gi.repository.GIRepository', module.name)
  module.graph.collect_modules('gi.overrides.' + repo_name, module.name)

  # TODO: Ability to examine the source file that imported the Gtk repository
  #       to determine the `require_version()` call.

  # TODO: Prevent duplicate records

  try:
    stack = [_get_typelib_info(repo_name, None)] # TODO: Version
  except pysubcmd.UnpicklableError as exc:
    if exc.type == 'GLib.Error':
      return # TODO: Warning?

  while stack:
    info = stack.pop(0)
    for dep in info['deps']:
      dep, version = dep.partition('-')[::2]
      module.graph.collect_modules('gi.repository.' + dep, module.name)
      stack.append(_get_typelib_info(dep, version))
    for lib in info['libs']:
      module.native_deps.append(Dependency(lib, None))\
    bundle.add_binary(info['typelib'])

  if not bundle.get_site_snippet('gi.repository'):
    bundle.add_site_snippet('gi.repository',
      "os.environ['GI_TYPELIB_PATH'] = sys.frozen_env['runtime_dir']")
