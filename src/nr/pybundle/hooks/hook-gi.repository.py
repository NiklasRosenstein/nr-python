
import os
import shutil
from nr.pybundle.nativedeps import Dependency
from nr.pybundle.utils import pysubcmd, system
from nr.pybundle.dist import copy_files_checked


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
    'libs': [x for x in info['sharedlib'].split(',') if x],
    'typelib': info['typelib'],
    'deps': info['deps']
  }
  typelib_data[(module, version)] = data
  return data


def examine(finder, module, results):
  repo_name = module.name[len('gi.repository.'):]
  if not repo_name: return
  results.imports.append('gi.overrides.' + repo_name)

  # TODO: Ability to examine the source file that imported the Gtk repository
  #       to determine the `require_version()` call.
  from gi._gi import Repository, RepositoryError
  repo = Repository.get_default()
  try:
    repo.require(repo_name)
  except RepositoryError:
    return # TODO: note? But can happen for conditional imports in GI source.

  # TODO: Prevent duplicate records

  stack = [_get_typelib_info(repo_name, None)] # TODO: Version
  while stack:
    info = stack.pop(0)
    for dep in info['deps']:
      dep, version = dep.partition('-')[::2]
      results.imports.append('gi.repository.' + dep)
      stack.append(_get_typelib_info(dep, version))
    for lib in info['libs']:
      module.native_deps.append(Dependency(lib, system.find_in_path(lib, common_ext=False)))
    # TODO: Inform the finder about this file, instead of copying it to the bundle directly.
    copy_files_checked(info['typelib'], 'bundle/runtime/' + os.path.basename(info['typelib']))
