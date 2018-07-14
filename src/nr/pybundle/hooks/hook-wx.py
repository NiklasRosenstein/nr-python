
from nr.pybundle import nativedeps
import os

# TODO: Option to include all of wxPython
# TODO: Add locale files when required/requested

def collect_data(module):
  if module.name != 'wx':
    return
  wx = module
  for mod in module.graph.filter(prefix='wx.', type=module.NATIVE):
    if not mod.imported_from: continue  # TODO: Unless wx:whole
    deps = nativedeps.Collection([wx.directory])
    deps.add(mod.filename)
    for dep in deps:
      if os.path.isfile(os.path.join(wx.directory, dep.name)):
        wx.package_data.append(dep.name)
