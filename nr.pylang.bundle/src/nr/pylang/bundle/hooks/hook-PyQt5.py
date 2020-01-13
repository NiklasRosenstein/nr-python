
"""
Hook to include all required files for PyQt5 -- or ONLY the required files
(to reduce the size of the resulting distribution).

Options:

* `PyQt5:whole` -- Just include the whole PyQt5 package. Must be set to `true`
"""

import collections
import os

from nr.pylang.bundle import nativedeps
from nr.databind.core import Struct
from nr.stream import Stream


class Module(Struct):
  __annotations__ = [
    ('deps', list, Named.Initializer(list)),
    ('files', list, Named.Initializer(list))
  ]


module_graph = collections.defaultdict(Module)
module_graph['QtBluetooth'].deps = []
module_graph['QtDBus'].deps = []
module_graph['QtDesigner'].deps = ['QtXml', 'QtWidgets']
module_graph['QtHelp'].deps = ['QtSql', 'QtWidgets']
module_graph['QtLocation'].deps = ['QtQuick', 'QtQml']
module_graph['QtMultimedia'].deps = ['QtNetwork', 'QtGui']
module_graph['QtMultimediaWidgets'].deps = ['QtMultimedia', 'QtWidgets', 'QtOpenGL']
module_graph['QtNetwork'].deps = []
module_graph['QtNetworkAuth'].deps = ['QtNetwork']
module_graph['QtNfc'].deps = []
module_graph['QtOpenGL'].deps = ['QtWidgets']
module_graph['QtPositioning'].deps = []
module_graph['QtPrintSupport'].deps = ['QtWidgets']
module_graph['QtQml'].deps = ['QtNetwork']
module_graph['QtQuick'].deps = ['QtQml', 'QtGui']
module_graph['QtQuickControls2'].deps = ['QtQuick']
module_graph['QtQuickParticles'].deps = ['QtQuick']
module_graph['QtQuickTemplates2'].deps = ['QtQuick']
module_graph['QtQuickTest'].deps = ['QtQuick']
module_graph['QtQuickWidgets'].deps = ['QtQuick', 'QtWidgets']
module_graph['QtSensors'].deps = []
module_graph['QtSerialPort'].deps = []
module_graph['QtSql'].deps = []
module_graph['QtSvg'].deps = ['QtWidgets']
module_graph['QtTest'].deps = []
module_graph['QtWebChannel'].deps = ['QtQml']
module_graph['QtWebEngine'].deps = ['QtWebChannel', 'QtWebEngineCore']
module_graph['QtWebEngineCore'].deps = ['QtQuick', 'QtNetwork', 'QtWebChannel', 'QtPositioning']
module_graph['QtWebEngineWidgets'].deps = ['QtWebEngineCore', 'QtQuickWidgets', 'QtQuick', 'QtWidgets', 'QtNetwork', 'QtPrintSupport']
module_graph['QtWebSockets'].deps = ['QtNetwork']
module_graph['QtWidgets'].deps = ['QtGui']
module_graph['QtWinExtras'].deps = ['QtGui']
module_graph['QtXml'].deps = []
module_graph['QtXmlPatterns'].deps = ['QtNetwork']

if os.name == 'nt':
  module_graph['QtOpenGL'].files = ['libEGL.dll', 'libGLESv2.dll', 'opengl32sw.dll']
  module_graph['QtWebEngineCore'].files = ['libeay32.dll', 'ssleay32.dll', 'd3dcompiler_47.dll', 'QtWebEngineProcess.exe']
  so_ext = '.dll'

# TODO: Other platforms


def _expand_modules(modules):
  result = set()
  stack = list(modules)
  while stack:
    name = stack.pop()
    if name not in result:
      stack.extend(module_graph[name].deps)
    result.add(name)
  return result


def _get_exclude_module_files(modules):
  modules = _expand_modules(modules)
  exclude = set(Stream.concat(x.files for x in module_graph.values()))
  for name in module_graph:
    if name not in modules:
      exclude.add('Qt5{}{}'.format(name[2:], so_ext))
  for name in modules:
    exclude -= set(module_graph.get(name, Module()).files)
  return exclude


def inspect_module(module):
  if module.name == 'PyQt5':
    module.zippable = False
    module.graph.collect_modules('sip', module.name)
    module.graph.collect_modules('PyQt5.sip', module.name)
    if options.get_bool('pyqt5:whole'):
      mod.include_package()


def collect_data(module, bundle):
  if module.name != 'PyQt5':
    module.skip_auto_native_deps = True
    module.graph.collect_modules('PyQt5')
    return

  bin_dir = os.path.join(module.directory, 'Qt', 'bin')
  bins = []

  if options.get_bool('pyqt5:whole'):
    module.package_data.append('Qt')
    bins += os.listdir(bin_dir)
  else:
    # TODO: Exclude plugins that will be unused
    module.package_data.append('Qt/plugins')

    # TODO: Remove unused PyQt5 submodules from finder.modules

    # Determine the PyQt components that the application actually uses.
    modules = set(['QtCore'])
    for mod in module.graph.filter(prefix='PyQt5.Qt', not_type=module.NOTFOUND):
      if mod.imported_from and mod.name.count('.') == 1:
        modules.add(mod.name.split('.')[1])
        bins.append(mod.filename)
    modules = _expand_modules(modules)
    [module.graph.collect_modules('PyQt5.' + x) for x in modules]

    # Discard unused modules.
    for mod in module.graph.filter(prefix='PyQt5.Qt'):
      if not mod.imported_from and mod.name.count('.') == 1 and \
          mod.name.split('.')[1] not in modules:
        self.graph.discard(mod.name)

    # Add only the necessary files from the bin/ directory.
    exclude_files = _get_exclude_module_files(modules)
    for name in os.listdir(bin_dir):
      if name not in exclude_files:
        module.package_data.append('Qt/bin/{}'.format(name))
        bins.append(os.path.join(bin_dir, name))

  deps = nativedeps.Collection([bin_dir])
  for name in bins:
    if nativedeps.is_binary(name):
      deps.add_dependencies_of(name)
  module.native_deps += deps.unresolved()
