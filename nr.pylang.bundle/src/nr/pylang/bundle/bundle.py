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


from dataclasses import dataclass, field
from nr.sumtype import add_constructor_tests, Constructor, Sumtype
from .hooks import Hook, DelegateHook
from .modules import ModuleInfo, ModuleGraph, ModuleFinder, ModuleImportFilter, get_core_modules, get_common_excludes
from .utils import gitignore, system
from .utils.fs import copy_files_checked
from . import nativedeps
from typing import Optional

import distlib.scripts
import json
import logging
import nr.fs
import os
import pkg_resources
import posixpath
import py_compile
import shlex
import shutil
import sys
import tqdm
import textwrap
import zipfile


def ensure_module_in_list(modules, graph, module_name):
  # type: (List[ModuleInfo], ModuleGraph, str)

  for module in graph:
    if module.type in (module.NOTFOUND, module.BUILTIN):
      continue
    if module.name == module_name or module.name.startswith(module_name + '.'):
      if module not in modules:
        modules.append(module)
        for import_ in module.imports:
          ensure_module_in_list(modules, graph, import_)


@dataclass
class AppResource:
  """
  Represents a file or directory that that is an application resource file
  and will need to be copied to the application folder.

  When the AppResource object is created, its *source* path normalized
  to ensure path comparisons work properly.
  """

  source: str  #: The path to the source file or directory.
  dest: str  #: The relative destination path in the bundle directory.

  def __init__(self, *args, **kwargs):
    super(AppResource, self).__init__(*args, **kwargs)
    self.source = nr.fs.canonical(self.source)


@dataclass
class SiteSnippet:
  """
  A code snippet that is inserted into the `site.py` module .
  """

  #: The name of the source that added the snippet. This can be the name
  #: of a hook, for example.
  source: str
  #: The code that will be added to the `site.py` module.
  code: str


@dataclass
class DirConfig:
  """
  The configuration where the bundle files will be placed.
  """

  bundle: Optional[str]
  lib: str
  lib_dynload: str = None
  runtime: str = None
  resource: str = None
  temp: str = '.bundler-temp'

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


@add_constructor_tests
class Entrypoint(Sumtype):
  """
  Represents an entrypoint specification of the format
  `[@]name=<spec> [args...]` where `<spec>` can be of the format
  `<module>:<function>` or `<filename>`.

  If the `@` is given, it specifies that the entrypoint is supposed to
  be executed in GUI mode.
  """

  File = Constructor('name filename args gui')
  Module = Constructor('name module function args gui')

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
        return cls.Module(name, module, function, args, gui)
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
      fp.write('#!/bin/sh\nhere=`dirname "$0"`\n"$here/runtime/python" "$here/{}.py"\n'.format(entrypoint.name))
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

    if 'site' not in self.modules:
      return

    mod = self.modules['site']

    with mod.append_file(nr.fs.join(self.dirconfig.temp, 'modules')) as fp:
      fp.write('\n')
      # Load the original contents of the site module.
      with open(self.modules['site'].filename) as src:
        fp.write(src.read())

      # Add our site code.
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


@dataclass
class DistributionBuilder:
  """
  This object handles building a distribution and contains most of the
  functionality that is also provided via the pybundle command-line.
  """

  collect: bool = False
  collect_to: str = None
  dist: bool = False
  pex_out: str = None
  #: The __main__.py for the generated PEX archive. This defaults to the
  #: pex_main.py that comes with the nr.pylang.bundle module.
  pex_main: str = nr.fs.join(nr.fs.dir(__file__), 'pex_main.py')
  #: An entrypoint for the script. This is parsed with the #Entrypoint
  #: class but it does not require the alias part (`xyz =`), and thus it
  #: can be just `module:member` or `filename`.
  pex_entrypoint: str = None
  #: The name of the console script that should serve as the entrypoint.
  #: This option cannot be used together with pex_entrypoint.
  pex_console_script: str = None
  pex_root: str = None
  pex_shebang: Optional[str] = '/usr/bin/env python' + sys.version[0]
  entries: list = field(default_factory=list)
  resources: list = field(default_factory=list)
  bundle_dir: str = 'bundle'
  excludes: list = field(default_factory=list)
  default_excludes: bool = True
  narrow: bool = False
  exclude_stdlib: bool = False
  exclude_in_path: list = field(default_factory=list)
  force_exclude_in_path: list = field(default_factory=list)
  includes: list = field(default_factory=list)
  whitelist: list = field(default_factory=list)
  default_includes: bool = True
  compile_modules: bool = False
  zip_modules: bool = False
  zip_file: str = None
  srcs: bool = True
  copy_always: bool = False
  module_path: list = field(default_factory=list)
  default_module_path: bool = True
  hooks_path: list = field(default_factory=list)
  default_hooks_path: bool = True
  hook_options: dict = field(default_factory=dict)
  logger: logging.Logger = logging.getLogger(__name__)
  fill_namespace_modules: bool = True

  def __post_init__(self):
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
    if self.narrow or self.exclude_stdlib:
      # TODO @nrosenstein Determine all the stdlib paths. This is just a
      #      method that seems to work on OSX.
      import os, contextlib
      try: import pickle as _pickle
      except ImportError: import cPickle as _pickle
      target = self.force_exclude_in_path if self.exclude_stdlib else self.exclude_in_path
      target.append(nr.fs.norm(nr.fs.dir(os.__file__)))
      target.append(nr.fs.norm(nr.fs.dir(contextlib.__file__)))
      target.append(nr.fs.norm(nr.fs.dir(_pickle.__file__)))
    if self.default_module_path:
      self.finder.path.insert(0, nr.fs.cwd())
      self.finder.path.extend(sys.path)
    if not self.default_hooks_path:
      self.hook.search_path = []
    self.finder.path += self.module_path
    self.filter.excludes += self.excludes
    self.hook.options.update(self.hook_options)
    self.hook.path += self.hooks_path

    if isinstance(self.pex_entrypoint, str):
      self.pex_entrypoint = Entrypoint.parse('alias=' + self.pex_entrypoint)
    if self.pex_console_script and self.pex_entrypoint:
      raise ValueError('pex_entrypoint and pex_console_script cannot be combined.')
    if self.pex_console_script:
      ep = next((x for x in pkg_resources.iter_entry_points('console_scripts')
        if x.name == self.pex_console_script), None)
      if not ep:
        raise ValueError('entrypoint "{}" does not exist in console_scripts group'
          .format(self.pex_console_script))
      self.pex_entrypoint = Entrypoint.Module(ep.name, ep.module_name, ep.attrs[0], [], False)
    if not self.pex_shebang:
      self.pex_shebang = type(self).pex_shebang

    if not self.logger:
      self.logger = logging.getLogger(__name__)

  def do_init_bundle(self):
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

  def do_get_modules(self):
    if not self.srcs and not self.compile_modules:
      raise ValueError('need either srcs=True or compile_modules=True')

    # Collect the list of modules to collect.
    modules = get_core_modules() if self.default_includes else []
    modules += self.includes
    modules += [x.module for x in self.bundle.entry_points if x.is_module()]
    if self.pex_out and self.pex_entrypoint and self.pex_entrypoint.is_module():
      modules.append(self.pex_entrypoint.module)

    # Collect a list of source files to collect from.
    source_files = []
    if self.pex_out:
      if self.pex_main:
        source_files.append(self.pex_main)
      if self.pex_entrypoint and self.pex_entrypoint.is_file():
        source_files.append(self.pex_entrypoint.filename)
    for ep in self.bundle.entry_points:
      if ep.is_file():
        source_files.append(ep.filename)

    # Collect the modules (with progress bar).
    print('Resolving input modules and scripts ...')
    progress = tqdm.tqdm(total=len(modules) + len(source_files))
    with progress:
      for module_name in modules:
        progress.set_description(module_name)
        progress.update(1)
        self.graph.collect_modules(module_name)
      for filename in source_files:
        progress.set_description(filename)
        progress.update(1)
        self.graph.collect_from_source(filename)

    # Make sure any entrypoints are collected as well.
    fetch_entrypoint_modules = set()
    for mod in self.graph:
      if mod.entry_points:
        for line in mod.entry_points.split('\n'):
          line = line.strip()
          if not line or line[0] in '[#' or '=' not in line:
            continue
          module = line.partition('=')[2].partition(':')[0].strip()
          fetch_entrypoint_modules.add(module)

    if fetch_entrypoint_modules:
      print('Resolving entrypoint modules ...')
      progress = tqdm.tqdm(total=len(fetch_entrypoint_modules))
      with progress:
        for module_name in fetch_entrypoint_modules:
          progress.set_description(module_name)
          progress.update(1)
          self.graph.collect_modules(module_name)

    print('Collecting module data...')
    self.graph.collect_data(self.bundle)

    if self.fill_namespace_modules:
      print('Filling up namespace modules ...')
      temp_modules_dir = nr.fs.join(self.dirconfig.temp, 'modules')
      for module in tqdm.tqdm(list(self.graph)):
        if module.parent or not module.parent_name:
          continue
        parent_name = module.name.rpartition('.')[0]
        parent = ModuleInfo(parent_name, '/:fill:/__init__.py', module.SRC)
        with parent.replace_file(temp_modules_dir) as fp:
          fp.write("__path__ = __import__('pkgutil').extend_path(__path__, __name__)\n")
        self.graph.add(parent)

    # Remove modules that are inside the excluded paths. We remove modules
    # from the bottom up (that's why we sort by name reversed).
    excluded_paths = set(nr.fs.norm(x) for x in self.exclude_in_path)
    for module in sorted(self.graph, key=lambda x: len(x.name), reverse=True):
      # TODO: What does this do again exactly? :) Add some docs Niklas, ffs!
      parent = module
      while parent.parent and parent.type == parent.NOTFOUND:
        parent = parent.parent
      if not parent.original_filename:
        continue
      path = nr.fs.norm(parent.get_lib_dir())
      if path in excluded_paths:
        module.exclude()

    # Force remove modules inside specified paths.
    excluded_paths = set(nr.fs.norm(x) for x in self.force_exclude_in_path)
    for module in self.graph:
      if module.original_filename and nr.fs.norm(module.get_lib_dir()) in excluded_paths:
        module.exclude()

  def report_module_stats(self):
    print('  {} modules found'.format(sum(1 for x in self.graph if x.type != x.NOTFOUND and x.type != x.BUILTIN)))
    print('  {} modules marked for exclusion'.format(sum(1 for x in self.graph.excluded() if x.type != x.NOTFOUND)))
    print('  {} modules not found (many of which may be member imports)'
          .format(sum(1 for x in self.graph if x.type == x.NOTFOUND)))

  def do_compile_modules(self, modules):
    if self.zip_modules:
      compile_dir = nr.fs.join(self.dirconfig.temp, 'compile-cache')
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

  def do_zip_modules(
      self,
      modules,
      zip_out=None,
      shebang=None,
  ):
    if not self.zip_file:
      self.zip_file = nr.fs.join(self.bundle_dir, 'libs.zip')
    zip_out = zip_out or self.zip_file

    # TODO: Exclude core modules that must be copied to the lib/
    #       directory anyway in the case of the 'dist' operation.
    # TODO: Also zip up package data?

    if shebang:
      print('Creating module zipball at "{}" ...'.format(zip_out))
    else:
      print('Creating PEX at "{}" ...'.format(zip_out))
    nr.fs.makedirs(nr.fs.dir(zip_out) or '.')

    if shebang:
      if nr.fs.isfile(zip_out):
        nr.fs.remove(zip_out)
      with open(zip_out, 'ab') as fp:
        fp.write(b'#!' + shebang.encode('ascii') + b'\n')
      zip_open_mode = 'a'
      zip_parent_dir = 'lib'
    else:
      zip_open_mode = 'w'
      zip_parent_dir = None

    not_zippable = []
    with zipfile.ZipFile(zip_out, zip_open_mode, zipfile.ZIP_DEFLATED) as zipf:
      for mod in modules:
        if mod.type in (mod.BUILTIN, mod.NOTFOUND):
          continue
        if not mod.is_zippable:
          not_zippable.append(mod)
          if not shebang:
            # We're not building a PEX, so we do not add this module to the ZIP.
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
          if zip_parent_dir:
            arcname = zip_parent_dir + '/' + arcname
          zipf.write(filename, arcname.replace(nr.fs.sep, '/'))

        # Write package data.
        ignore = gitignore.IgnoreList(mod.directory)
        ignore.parse(mod.package_data_ignore)

        def _write_package_data(filename):
          assert mod.is_pkg(), (mod.name, filename)
          rel = os.path.relpath(filename, mod.directory)
          arcname = posixpath.normpath(os.path.join(
            zip_parent_dir,
            mod.name.replace('.', '/'),
            rel).replace(nr.fs.sep, '/'))
          zipf.write(filename, arcname)

        for name in mod.package_data:
          src = nr.fs.join(mod.directory, name)
          if nr.fs.isfile(src):
            _write_package_data(src)
          elif nr.fs.isdir(src):
            for root, dirs, files in os.walk(src):
              for filename in files:
                src_file = nr.fs.norm(nr.fs.join(root, filename))
                rel_file = nr.fs.rel(src_file, src)
                if ignore.is_ignored(rel_file, False):
                  continue
                _write_package_data(src_file)
          else:
            self.logger.warning('package_data "%s" for module "%s" does not '
              'exist (full path: "%s")',
              name, mod.name, src)

        # Write the entrypoints.
        if mod.entry_points:
          with nr.fs.tempfile(text=True) as fp:
            print('Writing entrypoints for', mod.name)
            fp.write(mod.entry_points)
            fp.close()
            arcname = posixpath.join(zip_parent_dir, mod.name + '.egg-info', 'entry_points.txt')
            zipf.write(fp.name, arcname)

      if shebang and self.pex_entrypoint and self.pex_entrypoint.is_file():
        zip_entrypoint = 'run/' + nr.fs.base(self.pex_entrypoint.filename)
        zipf.write(self.pex_entrypoint.filename, zip_entrypoint)
      else:
        zip_entrypoint = None

      if shebang:
        if self.pex_entrypoint and self.pex_entrypoint.is_file():
          entrypoint = {
            'type': 'file',
            'path': zip_entrypoint,
            'args': self.pex_entrypoint.args,
            'gui': self.pex_entrypoint.gui}
        elif self.pex_entrypoint and self.pex_entrypoint.is_module():
          entrypoint = {
            'type': 'module',
            'module': self.pex_entrypoint.module,
            'member': self.pex_entrypoint.function,
            'args': self.pex_entrypoint.args,
            'gui': self.pex_entrypoint.gui}
        elif self.pex_console_script:
          entrypoint = {
            'type': 'console_script',
            'name': self.pex_console_script}
        zipf.write(self.pex_main, '__main__.py')
        with nr.fs.tempfile(text=True) as fp:
          fp.write(json.dumps({
            'unzip_modules': list(set([x.get_namespace_root().name for x in not_zippable])),
            'entrypoint': entrypoint,
            'root': self.pex_root,
            'lib': zip_parent_dir
          }))
          fp.close()
          zipf.write(fp.name, 'PEX-INFO')

    if shebang:
      nr.fs.chmod(zip_out, '+x')

    if not_zippable and not shebang:
      print('Note: There are modules that can not be zipped, they will be copied into the lib/ folder.')
    else:
      print('Note: There are modules that cannot be used from inside the PEX.')
      print('  They will be extracted into a temporary folder when the PEX is invoked.')

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
      ignore = gitignore.IgnoreList(mod.directory)
      ignore.parse(mod.package_data_ignore)
      for name in mod.package_data:
        src = nr.fs.join(mod.directory, name)
        dst = nr.fs.join(lib_dir, mod.relative_directory, name)
        copy_files_checked(src, dst, self.copy_always, ignore)

      # Write the entrypoints data.
      if mod.entry_points:
        dist_info_dir = nr.fs.join(lib_dir, mod.name + '.egg-info')
        nr.fs.makedirs(dist_info_dir)
        with open(nr.fs.join(dist_info_dir, 'entry_points.txt'), 'w') as fp:
          print('Writing entrypoints for', mod.name)
          fp.write(mod.entry_points)

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

  def do_pex(self):
    modules = [x for x in self.graph if not x.excludes]
    self.do_zip_modules(
      modules,
      zip_out=self.pex_out,
      shebang=self.pex_shebang)

  def build(self):
    did_stuff = False
    self.do_init_bundle()

    if self.dist or self.collect:
      did_stuff = True
      self.do_get_modules()
      self.report_module_stats()

    if self.dirconfig.bundle:
      self.bundle.prepare()

    if self.dist or self.collect:
      modules = [x for x in self.graph if x.type not in (x.NOTFOUND, x.BUILTIN) and not x.excludes]
      if self.dist:
        # We need the "os" module as Python uses it to determine where the
        # standard library is located, as well as other core modules.
        for name in (get_core_modules() if self.default_includes else []):
          ensure_module_in_list(modules, self.graph, name.rstrip('+'))
      if self.compile_modules and modules:
        self.do_compile_modules(modules)
      if self.zip_modules and modules:
        # Some of the modules may need to be copied.
        modules = self.do_zip_modules(modules)
      if modules:
        self.do_copy_modules(modules)

    if self.dist:
      self.do_dist()
    if self.pex_out:
      did_stuff = True
      self.do_pex()

    if self.dirconfig.bundle:
      self.bundle.create_bundle(self.copy_always)

    return did_stuff
