# -*- coding: utf8 -*-
# The MIT License (MIT)
#
# Copyright (c) 2018 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

from nr.types import record, sumtype
from .hooks import Hook, DelegateHook
from .modules import ModuleGraph, ModuleFinder, ModuleImportFilter, get_core_modules, get_common_excludes
from .utils import system
from .utils.fs import copy_files_checked
from . import nativedeps

import distlib.scripts
import logging
import nr.fs
import py_compile
import shlex
import shutil
import sys
import textwrap
import zipfile


class AppResource(record):
  """
  Represents a file or directory that that is an application resource file
  and will need to be copied to the application folder.

  When the AppResource object is created, its *source* path normalized
  to ensure path comparisons work properly.
  """

  __annotations__ = [
    ('source', str),  #: The path to the source file or directory.
    ('dest', str),  #: The relative destination path in the bundle directory.
  ]

  def __init__(self, *args, **kwargs):
    super(AppResource, self).__init__(*args, **kwargs)
    self.source = nr.fs.canonical(self.source)


class SiteSnippet(record):
  """
  A code snippet that is inserted into the `site.py` module .
  """

  __annotations__ = [
    #: The name of the source that added the snippet. This can be the name
    #: of a hook, for example.
    ('source', str),
    #: The code that will be added to the `site.py` module.
    ('code', str),
  ]


class DirConfig(record):
  """
  The configuration where the bundle files will be placed.
  """

  __annotations__ = [
    ('bundle', str, None),
    ('lib', str),
    ('lib_dynload', str, None),
    ('runtime', str, None),
    ('resource', str, None)
  ]

  @classmethod
  def for_collect_to(cls, path):
    return cls(None, path, path, None, None)

  @classmethod
  def for_bundle(cls, bundle_dir):
    if system.is_unix:
      lib = nr.fs.join(bundle_dir, 'lib/python{}'.format(sys.version[:3]))
      lib_dynload = nr.fs.join(lib, 'lib-dynload')
    else:
      lib = nr.fs.join(bundle_dir, 'lib')
      lib_dynload = lib
    return cls(bundle_dir, lib, lib_dynload, nr.fs.join(bundle_dir, 'runtime'),
               nr.fs.join(bundle_dir, 'res'))


class Entrypoint(sumtype):
  """
  Represents an entrypoint specification of the format
  `[@]name=<spec> [args...]` where `<spec>` can be of the format
  `<module>:<function>` or `<filename>`.

  If the `@` is given, it specifies that the entrypoint is supposed to
  be executed in GUI mode.
  """

  File = sumtype.constructor('name filename args gui')
  Qid = sumtype.constructor('name module function args gui')

  def distlib_spec(self):
    if self.is_file():
      return '{}={}'.format(self.name, self.filename)
    else:
      return '{}={}:{}'.format(self.name, self.module, self.function)

  @classmethod
  def parse(cls, spec):
    argv = shlex.split(spec)
    if not argv or '=' not in argv[0]:
      raise ValueError('invalid entrypoint spec: {!r}'.format(spec))
    name, remainder = argv[0].partition('=')[::2]
    gui = name.startswith('@')
    if gui:
      name = name[1:]
    if not name or not remainder:
      raise ValueError('invalid entrypoint spec: {!r}'.format(spec))
    args = argv[1:]
    if ':' in remainder:
      module, function = remainder.partition(':')[::2]
      if module and function:
        return cls.Qid(name, module, function, args, gui)
    else:
      return cls.File(name, remainder, args, gui)
    raise ValueError('invalid entrypoint spec: {!r}'.format(spec))


class ScriptMaker(object):
  """
  This class is used to generate Python scripts that can be executed by
  users. On Windows, it will use the #distlib.scripts.ScriptMaker class
  which can produce an executable, on other platforms it will produce a
  shell script.
  """

  # TODO: In a GUI based script, wrap all of it in a try-catch
  #       block and show the error in a message box.
  script_template = textwrap.dedent('''
    import sys, site
    if hasattr(site, 'rthooks'):
      site.rthooks()
    args = {args}
    module = __import__('{module_name}')
    for name in '{module_name}'.split('.')[1:]:
      module = getattr(module, name)
    func = getattr(module, '{func_name}')
    sys.argv = [sys.argv[0]] + args + sys.argv[1:]
    sys.exit(func())
  ''').strip()

  def __init__(self, executable, target_dir, source_dir=None):
    self.executable = executable
    self.target_dir = target_dir
    self.source_dir = source_dir

  def make_script(self, entrypoint):
    if isinstance(entrypoint, str):
      entrypoint = Entrypoint.parse(entrypoint)
    # TODO: We want to produce an executable on any Windows environment,
    #       but on MSYS and Cygwin, distlib.scripts.ScriptMaker will produce
    #       a bash script that doesn't work properly with relative shebangs.
    if system.is_purewin:
      maker = distlib.scripts.ScriptMaker(self.source_dir, self.target_dir)
      maker.variants = set([''])
      maker.script_template = self.script_template.format(
        args=repr(entrypoint.args), module_name='%(module)s',
        func_name='%(func)s')
      maker.executable = self.executable
      maker.make(entrypoint.distlib_spec(), options={'gui': entrypoint.gui})
      return

    nr.fs.makedirs(self.target_dir)
    script = nr.fs.join(self.target_dir, '{}.py'.format(entrypoint.name))
    with open(script, 'w') as fp:
      if entrypoint.is_file():
        # TODO
        raise NotImplementedError
      else:
        fp.write(self.script_template.format(
          args=repr(entrypoint.args),
          module_name=entrypoint.module,
          func_name=entrypoint.function))

    if system.is_win:
      batch = nr.fs.join(self.target_dir, '{}.bat'.format(entrypoint.name))
      with open(batch, 'w') as fp:
        fp.write('@call "%~dp0runtime\\python.exe" "%~dp0\\{}.py'.format(entrypoint.name))

    sh = nr.fs.join(self.target_dir, entrypoint.name)
    with open(sh, 'w') as fp:
      fp.write('#!/bin/sh\nhere=`dirname "$0"`\n"$here/runtime/python" "$here/test.py"\n')
    nr.fs.chmod(sh, '+x')


class PythonAppBundle(object):
  """
  In the PythonAppBundle we collect all required information to produce a
  standalone Python applicaton.

  # Attributes

  logger (logging.Logger)

  dirconfig (DirConfig)

    A #DirConfig object with the paths to the bundle directories.

  scripts (ScriptMaker)

    A #ScriptMaker instance.

  modules (ModuleGraph)

    The container for the information on all collected Python modules that
    are being included in the bundle.

  resources (list of AppResource)

    A list of application resource files. If the #AppResource.dest member
    is #None, it will fall back to the basename of the #AppResource.source
    inside the applications `res/` directory. Relative paths in
    #AppResource.dest are assumed relative to the application bundle
    directory.

  binaries (list of AppResource)

    A list of application binary files. If the #AppResource.dest member is
    #None, it will fall back to the basename of the #AppResource.source
    inside the applications `runtime/` directory. Relative paths in the
    #AppResource.dest are assumed relative to the application runtime
    directory.

  site_snippets (list of SiteSnippet)

    A list of code snippets that will be injected into the `site.py` module
    of the Python bundle. The `sys` and `os` modules are garuanteed to be
    available for the code snippets.

  entry_points (list of Entrypoint)

    A list of #Entrypoint objects that specify entry points for the
    application.
  """

  def __init__(self, dirconfig, scripts, modules, logger=None):
    self.logger = logger or logging.getLogger(__name__)
    self.dirconfig = dirconfig
    self.scripts = scripts
    self.modules = modules
    self.resources = []
    self.binaries = []
    self.site_snippets = []
    self.rthooks = []
    self.entry_points = []

  def add_resource(self, source, dest=None):
    add = True
    resource = AppResource(source, dest)
    for res in self.resources:
      if res.source == resource.source:
        if res.dest != resource.dest:
          self.logger.warn('PythonAppBundle.add_resource(): Resource '
            '{!r} already added but the destination differs ({!r} != {!r}). '
            .format(res.source, res.dest, resource.dest))
        else:
          add = False
        break
    if add:
      self.resources.append(resource)

  def add_binary(self, source, dest=None):
    add = True
    resource = AppResource(source, dest)
    for res in self.binaries:
      if res.source == resource.source:
        if res.dest != resource.dest:
          self.logger.warn('PythonAppBundle.add_binary(): Binary '
            '{!r} already added but the destination differs ({!r} != {!r}). '
            .format(res.source, res.dest, resource.dest))
        else:
          add = False
        break
    if add:
      self.binaries.append(resource)

  def get_site_snippet(self, source):
    for snippet in self.site_snippets:
      if snippet.source == source:
        return source
    return None

  def add_site_snippet(self, source, code):
    self.site_snippets.append(SiteSnippet(source, code))

  def get_rthook(self, source):
    for snippet in self.rthooks:
      if snippet.source == source:
        return source
    return None

  def add_rthook(self, source, code):
    self.rthooks.append(SiteSnippet(source, code))

  def add_entry_point(self, spec):
    if isinstance(spec, str):
      spec = Entrypoint.parse(spec)
    for other in self.entry_points:
      if other.name == spec.name:
        self.logger.warn('PythonAppBundle.add_entry_point(): An entry-point '
            'with the name {!r} is already specified.'.format(spec.name))
        break
    self.entry_points.append(spec)

  def prepare(self):
    """
    Prepare the bundle. This method currently only creates a substitute
    `site` module that contains the site snippets added to the bundle.
    """

    if not 'site' in self.modules:
      return

    import atexit  # TODO: Maybe create a context manager for the PythonAppBundle instead
    fp = nr.fs.tempfile('.py', text=True)
    fp.__enter__()
    atexit.register(lambda: fp.__exit__(None, None, None))

    with open(self.modules['site'].filename) as src:
      fp.write(src.read())

    fp.write('\n\n')
    for snippet in self.site_snippets:
      fp.write('###@@@ Site-Snippet: {}\n'.format(snippet.source))
      fp.write(snippet.code.rstrip())
      fp.write('\n\n')
    fp.write('def rthooks():\n')
    fp.write('  " Runtime-hooks installed from nr.pybundle hooks. "\n')
    for snippet in self.rthooks:
      fp.write('  ###@@@ RtHook: {}\n'.format(snippet.source))
      for line in snippet.code.split('\n'):
        fp.write('  {}\n'.format(line))
      fp.write('\n')
    fp.close()

    self.modules['site'].filename = fp.name

  def create_bundle(self, copy_always):
    """
    Create the bundle by copying all resource files, binaries and creating
    entrypoints.
    """

    assert self.dirconfig.bundle

    # TODO: Do most of the stuff from the #DistributionBuilder here,
    #       like copying module files etc.

    for res in self.resources:
      if not res.dest:
        res.dest = nr.fs.abs(nr.fs.join(self.dirconfig.resource, nr.fs.base(res.source)))
      res.dest = nr.fs.join(self.dirconfig.bundle, res.dest)
      copy_files_checked(res.source, res.dest, copy_always)
    for res in self.binaries:
      if not res.dest:
        res.dest = nr.fs.abs(nr.fs.join(self.dirconfig.runtime, nr.fs.base(res.source)))
      res.dest = nr.fs.join(self.dirconfig.bundle, res.dest)
      copy_files_checked(res.source, res.dest, copy_always)
    for ep in self.entry_points:
      self.scripts.make_script(ep)


class DistributionBuilder(record):
  """
  This object handles building a distribution and contains most of the
  functionality that is also provided via the pybundle command-line.
  """

  __annotations__ = [
    ('collect', bool, False),
    ('collect_to', str, None),
    ('dist', str, False),
    ('entries', list, ()),
    ('resources', list, ()),
    ('bundle_dir', str, 'bundle'),
    ('excludes', list, ()),
    ('default_excludes', bool, True),
    ('includes', list, ()),
    ('whitelist', list, ()),
    ('default_includes', bool, True),
    ('compile_modules', bool, False),
    ('zip_modules', bool, False),
    ('zip_file', str, None),
    ('srcs', bool, True),
    ('copy_always', bool, False),
    ('module_path', list, ()),
    ('default_module_path', bool, True),
    ('hooks_path', list, ()),
    ('default_hooks_path', bool, True),
    ('hook_options', dict, lambda: {}),
    ('logger', logging.Logger, None)
  ]

  def __init__(self, *args, **kwargs):
    super(DistributionBuilder, self).__init__(*args, **kwargs)
    self.python_bins = system.get_python_executables()
    self.python_bin = next(k for k in self.python_bins if 'w' not in k)
    self.includes = list(self.includes)
    self.finder = ModuleFinder([])
    self.filter = ModuleImportFilter(self.excludes, self.whitelist)
    self.hook = DelegateHook()
    self.graph = ModuleGraph(self.finder, self.filter, self.hook)

    if self.collect_to:
      self.dirconfig = DirConfig.for_collect_to(self.collect_to)
      self.collect = True
      self.bundle = None
      if self.dist:
        raise ValueError('collect_to can not be combined with dist')
    else:
      self.dirconfig = DirConfig.for_bundle(self.bundle_dir)

    self.bundle = PythonAppBundle(
      dirconfig = self.dirconfig,
      scripts = ScriptMaker(
        nr.fs.join('runtime', nr.fs.base(self.python_bin)),
        self.bundle_dir),
      modules = self.graph)

    if self.default_excludes:
      self.filter.excludes += get_common_excludes()
    if self.default_module_path:
      self.finder.path.insert(0, nr.fs.cwd())
      self.finder.path.extend(sys.path)
    if not self.default_hooks_path:
      self.hook.search_path = []
    self.finder.path += self.module_path
    self.filter.excludes += self.excludes
    self.hook.options.update(self.hook_options)
    self.hook.path += self.hooks_path

    if not self.logger:
      self.logger = logging.getLogger(__name__)

  def do_compile_modules(self, modules):
    if self.zip_modules:
      compile_dir = nr.fs.join(self.bundle_dir, '.compile-cache')
    else:
      compile_dir = self.dirconfig.lib
    print('Compiling modules in "{}" ...'.format(compile_dir))
    for mod in modules:
      if mod.type == mod.SRC:
        dst = nr.fs.join(compile_dir, mod.relative_filename + 'c')
        mod.compiled_file = dst
        if self.copy_always or nr.fs.compare_timestamp(mod.filename, dst):
          nr.fs.makedirs(nr.fs.dir(dst))
          py_compile.compile(mod.filename, dst, doraise=True)

  def do_zip_modules(self, modules):
    if not self.zip_file:
      self.zip_file = nr.fs.join(self.bundle_dir, 'libs.zip')

    # TODO: Exclude core modules that must be copied to the lib/
    #       directory anyway in the case of the 'dist' operation.
    # TODO: Also zip up package data?

    print('Creating module zipball at "{}" ...'.format(self.zip_file))
    not_zippable = []
    with zipfile.ZipFile(self.zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
      for mod in modules:
        if not mod.is_zippable:
          not_zippable.append(mod)
          continue

        if mod.type == mod.SRC:
          files = []
          if self.srcs:
            files.append((mod.relative_filename, mod.filename))
          if self.compile_modules:
            files.append((mod.relative_filename + 'c', mod.compiled_file))
          assert files
        else:
          files = [(mod.relative_filename, mod.filename)]

        for arcname, filename in files:
          zipf.write(filename, arcname.replace(os.sep, '/'))

    if not_zippable:
      print('Note: There are modules that can not be zipped, they will be copied into the lib/ folder.')
    return not_zippable

  def do_copy_modules(self, modules):
    lib_dir = self.dirconfig.lib
    lib_dynload_dir = self.dirconfig.lib_dynload
    print('Copying modules to "{}" ...'.format(lib_dir))
    for mod in modules:
      # Copy the module itself.
      src = mod.filename
      dst = nr.fs.join(lib_dir, mod.relative_filename)
      if mod.type == mod.SRC and not self.srcs:
        src = mod.compiled_file
        dst += 'c'
      elif mod.type == mod.NATIVE and mod.name.count('.') == 0:
        dst = nr.fs.join(lib_dynload_dir, mod.relative_filename)
      if self.copy_always or nr.fs.compare_timestamp(src, dst):
        nr.fs.makedirs(nr.fs.dir(dst))
        shutil.copy(src, dst)

      # Copy package data.
      ignore = nr.gitignore.IgnoreList(mod.directory)
      ignore.parse(mod.package_data_ignore)
      for name in mod.package_data:
        src = nr.fs.join(mod.directory, name)
        dst = nr.fs.join(lib_dir, mod.relative_directory, name)
        copy_files_checked(src, dst, self.copy_always, ignore)

  def do_dist(self):
    print('Analyzing native dependencies ...')
    deps = nativedeps.Collection(exclude_system_deps=True)

    # Compile a set of all the absolute native dependencies to exclude.
    stdpath = lambda x: nr.fs.norm(nr.fs.fixcase(x)).lower()
    native_deps_exclude = set()
    # TODO
    #for mod in self.graph:
    #  native_deps_exclude.update(stdpath(x) for x in mod.native_deps_exclude)

    # Resolve dependencies.
    search_path = deps.search_path
    for name, path in self.python_bins.items():
      dep = deps.add(path, recursive=True)
      dep.name = name
    for mod in self.graph:
      if mod.type == mod.NATIVE and not mod.skip_auto_native_deps:
        deps.add(mod.filename, dependencies_only=True, recursive=True)
      for dep in mod.native_deps:
        deps.add(dep, recursive=True)

    # Warn about dependencies that can not be found.
    notfound = 0
    for dep in deps:
      if not dep.filename:
        notfound += 1
        self.logger.warn('Native dependency could not be found: {}'.format(dep.name))
    if notfound != 0:
      self.logger.error('{} native dependencies could not be found.'.format(notfound))

    runtime_dir = nr.fs.join(self.bundle_dir, 'runtime')
    print('Copying Python interpreter and native dependencies to "{}"...'.format(runtime_dir))
    nr.fs.makedirs(runtime_dir)
    for dep in deps:
      if dep.filename and stdpath(dep.filename) not in native_deps_exclude:
        dst = nr.fs.join(runtime_dir, nr.fs.base(dep.name))
        if self.copy_always or nr.fs.compare_timestamp(dep.filename, dst):
          shutil.copy(dep.filename, dst)

  def build(self):
    did_stuff = False

    if self.entries:
      did_stuff = True
      for entrypoint in self.entries:
        self.bundle.add_entry_point(entrypoint)

    if self.resources:
      did_stuff = True
      for path in self.resources:
        src, dst = path.partition(':')[::2]
        if not dst: dst = None
        self.bundle.add_resource(src, dst)

    if self.dist or self.collect:
      did_stuff = True
      if not self.srcs and not self.compile_modules:
        raise ValueError('need either srcs=True or compile_modules=True')

      print('Resolving dependencies ...')
      modules = get_core_modules() if self.default_includes else []
      modules += self.includes
      modules += [x.module for x in self.bundle.entry_points if x.is_qid()]
      for module_name in modules:
        self.graph.collect_modules(module_name)
      self.graph.collect_data(self.bundle)

      print('  {} modules found'.format(sum(1 for x in self.graph if x.type != x.NOTFOUND)))
      print('  {} modules not found (many of which may be member imports)'
            .format(sum(1 for x in self.graph if x.type == x.NOTFOUND)))

    if self.dirconfig.bundle:
      self.bundle.prepare()

    if self.dist or self.collect:
      modules = [x for x in self.graph if x.type not in (x.NOTFOUND, x.BUILTIN)]
      if self.compile_modules and modules:
        self.do_compile_modules(modules)
      if self.zip_modules and modules:
        # Some of the modules may need to be copied.
        modules = self.do_zip_modules(modules)
      if modules:
        self.do_copy_modules(modules)

    if self.dist:
      self.do_dist()

    if self.dirconfig.bundle:
      self.bundle.create_bundle(self.copy_always)

    return did_stuff
