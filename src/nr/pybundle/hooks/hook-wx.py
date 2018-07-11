
from nr.pybundle import nativedeps
import os


def finalize(finder):
  # TODO: Option to include all of wxPython
  # TODO: Add locale files when required/requested
  wx = finder.modules['wx']
  for mod in list(finder.modules.values()):
    if mod.natural and mod.type == mod.NATIVE:
      deps = nativedeps.Collection()
      deps.search_path = wx.directory
      deps.add(mod.filename)
      for dep in deps:
        if os.path.isfile(os.path.join(wx.directory, dep.name)):
          wx.package_data.append(dep.name)
    if not mod.natural:
      del finder.modules[mod.name]
