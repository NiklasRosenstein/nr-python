
import collections
import os
from nr.stream import stream
from nr.types import Named

class Module(Named):
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
  exclude = set(stream.concat(x.files for x in module_graph.values()))
  for name in module_graph:
    if name not in modules:
      exclude.add('Qt5{}{}'.format(name[2:], so_ext))
  for name in modules:
    exclude -= set(module_graph.get(name, Module()).files)
  return exclude


def examine(finder, module, result):
  if module.name == 'PyQt5':
    result.imports.append('sip')
    result.modules += finder.iter_package_modules(module)


def finalize(finder):
  module = finder.modules['PyQt5']
  module.zippable = False

  # Make sure the Qt libraries can be found by the native dependency
  # resolution but also that they are not copied into the runtime directory.
  bin_dir = os.path.join(module.directory, 'Qt', 'bin')
  module.native_deps_path.append(bin_dir)
  for name in os.listdir(bin_dir):
    module.native_deps_exclude.append(os.path.join(bin_dir, name))

  whole_qt = False # TODO: Option to just include all modules.
  if whole_qt:
    module.package_data.append('Qt/bin')
  else:
    # From the used imports, determine the Qt modules that are required.
    modules = set(['QtCore'])
    for mod in finder.modules.values():
      if mod.natural and mod.name.startswith('PyQt5.Qt') and mod.name.count('.') == 1:
        name = mod.name.split('.')[1]
        modules.add(name)

    # Add only the necessary files from the bin/ directory.
    exclude_files = _get_exclude_module_files(modules)
    for name in os.listdir(bin_dir):
      if name not in exclude_files:
        module.package_data.append('Qt/bin/{}'.format(name))

  module.package_data.append('Qt/plugins')  # TODO: Exclude plugins that will be unused
