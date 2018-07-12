
import logging
import nr.fs
import nr.types
import os
import py_compile
import re
import shlex
import shutil
import sys
import zipfile

from distlib.scripts import ScriptMaker as _ScriptMaker
from nr.stream import stream
from . import nativedeps
from .utils import system
from .modules import ModuleInfo, ModuleFinder, core_libs, common_excludes


class BundleConfig(nr.types.Named):
  __annotations__ = [
    ('lib_dir', str),
    ('lib_dynload_dir', str)
  ]


if system.is_unix:
  bundleconf = BundleConfig(
    'lib/python{}'.format(sys.version[:3]),
    'lib/python{}/lib-dynload'.format(sys.version[:3])
  )
else:
  bundleconf = BundleConfig(
    'lib',
    'lib'
  )


SCRIPT_TEMPLATE = '''
if __name__ == '__main__':
  import sys
  args = {args!r}
  module = __import__('%(module)s')
  for name in '%(module)s'.split('.')[1:]:
    module = getattr(module, name)
  func = getattr(module, '%(func)s')
  sys.argv = [sys.argv[0]] + args + sys.argv[1:]
  sys.exit(func())
'''.strip()


def make_script(shebang, dirname, spec, gui=False):
  result = {'modules': [], 'files': []}
  spec = shlex.split(spec)
  if '=' in spec[0]:
    # We assume that it is a Python entrypoint specification.
    match = re.match('^[\w_\.\-]+=([\w_\.]+):[\w_\.]+$', spec[0])
    if not match:
      raise ValueError('invalid entrypoint spec: {!r}'.format(spec))
    result['modules'].append(match.group(1))
  else:
    if ':' in spec[0]:
      raise ValueError('invalid entrypoint spec: {!r}'.format(spec))
    result['files'].append(spec[0])

  # TODO: The shebang passed to the ScriptMaker here won't be useful
  #       on unix systems as the relative path will not be taken into
  #       account from the parent directory of the script.
  maker = _ScriptMaker(os.getcwd(), dirname)
  maker.script_template = SCRIPT_TEMPLATE.format(args=spec[1:])
  maker.executable = shebang
  maker.variants = set([''])
  maker.make(spec[0], options={'gui': gui})
  return result


def copy_files_checked(src, dst, force=False):
  """
  Copies the contents of directory *src* into *dst* recursively. Files that
  already exist in *dst* will be timestamp-compared to avoid unnecessary
  copying, unless *force* is specified.

  Returns the number the total number of files and the number of files
  copied.
  """

  total_files = 0
  copied_files = 0

  if os.path.isfile(src):
    total_files += 1
    if force or nr.fs.compare_timestamp(src, dst):
      nr.fs.makedirs(os.path.dirname(dst))
      shutil.copyfile(src, dst)
      copied_files += 1
  else:
    for srcroot, dirs, files in os.walk(src):
      dstroot = os.path.join(dst, os.path.relpath(srcroot, src))
      for filename in files:
        srcfile = os.path.join(srcroot, filename)
        dstfile = os.path.join(dstroot, filename)

        total_files += 1
        if force or nr.fs.compare_timestamp(srcfile, dstfile):
          nr.fs.makedirs(dstroot)
          shutil.copyfile(srcfile, dstfile)
          copied_files += 1

  return total_files, copied_files


class PyBundle(nr.types.Named):
  """
  This class can be filled with all the information for producing a standalone
  Python distribution.
  """

  __annotations__ = [
    ('collect', str, False),
    ('dist', str, False),
    ('entries', list, ()),
    ('wentries', list, ()),
    ('resources', list, ()),
    ('bundle_dir', str, 'bundle'),
    ('excludes', list, ()),
    ('default_excludes', bool, True),
    ('includes', list, ()),
    ('default_includes', bool, True),
    ('compile_modules', bool, False),
    ('zip_modules', bool, False),
    ('zip_file', str, None),
    ('srcs', bool, True),
    ('sparse', bool, False),
    ('copy_always', bool, False),
    ('module_path', list, ()),
    ('default_module_path', bool, True),
    ('hooks_path', list, ()),
    ('default_hooks_path', bool, True),
    ('hook_options', dict, nr.types.Named.Initializer(dict)),
    ('logger', logging.Logger, None)
  ]

  def __init__(self, *args, **kwargs):
    super(PyBundle, self).__init__(*args, **kwargs)
    self.python_bins = system.get_python_executables()
    self.python_bin = next(k for k in self.python_bins if 'w' not in k)
    self.includes = list(self.includes)

    finder = self.finder = ModuleFinder(excludes=common_excludes)
    if not self.default_excludes:
      finder.excludes = []
    if self.default_module_path:
      finder.path.insert(0, os.getcwd())
    else:
      finder.path = []
    if not self.default_hooks_path:
      finder.hooks.search_path = []
    finder.path += self.module_path
    finder.hooks.options.update(self.hook_options)
    finder.hooks.search_path += self.hooks_path
    finder.excludes += self.excludes

    if not self.logger:
      self.logger = logging.getLogger(__name__)

  def build(self):
    did_stuff = False

    if self.entries or self.wentries:
      did_stuff = True
      python_bin = os.path.join('runtime', os.path.basename(self.python_bin))
      for spec in self.entries:
        data = make_script(python_bin, self.bundle_dir, spec, gui=False)
        self.includes += data['modules']
        # TODO: Take imports of data['files'] into account
      for spec in self.wentries:
        data = make_script(python_bin, self.bundle_dir, spec, gui=True)
        self.includes += data['modules']
        # TODO: Take imports of data['files'] into account

    if self.resources:
      did_stuff = True
      for path in self.resources:
        src, dst = path.partition(':')[::2]
        if not dst:
          dst = os.path.join('res', os.path.basename(src))
        copy_files_checked(src, os.path.join(self.bundle_dir, dst), self.copy_always)

    if self.dist or self.collect:
      did_stuff = True
      if not self.srcs and not self.compile_modules:
        raise ValueError('need either srcs=True or compile_modules=True')

      print('Resolving dependencies ...')
      modules = list(core_libs) if self.default_includes else []
      modules += self.includes
      self.finder.find_modules(modules, sparse=self.sparse)
      self.finder.finalize()

      notfound = 0
      modules = []
      for mod in self.finder.modules.values():
        if mod.type == mod.NOTFOUND:
          self.logger.warn('Module could not be found: {}'.format(mod.name))
          notfound += 1
        elif mod.type != mod.BUILTIN:
          modules.append(mod)
      if notfound != 0:
        self.logger.error('{} modules could not be found.'.format(notfound))
        self.logger.error("But do not panic, most of them are most likely imports "
                          "that are platform dependent or member imports.")
        self.logger.error('Increase the verbosity with -v, --verbose for details.')

      lib_dir = os.path.join(self.bundle_dir, bundleconf.lib_dir)
      lib_dynload_dir = os.path.join(self.bundle_dir, bundleconf.lib_dynload_dir)
      if self.zip_modules:
        compile_dir = os.path.join(self.bundle_dir, '.compile-cache')
      else:
        compile_dir = lib_dir

      if self.compile_modules and modules:
        print('Compiling modules in "{}" ...'.format(compile_dir))
        for mod in modules:
          if mod.type == mod.SRC:
            dst = os.path.join(compile_dir, mod.relative_filename + 'c')
            mod.compiled_file = dst
            if self.copy_always or nr.fs.compare_timestamp(mod.filename, dst):
              nr.fs.makedirs(os.path.dirname(dst))
              py_compile.compile(mod.filename, dst, doraise=True)

      if self.zip_modules and modules:
        if not self.zip_file:
          self.zip_file = os.path.join(self.bundle_dir, 'libs.zip')

        # TODO: Exclude core modules that must be copied to the lib/
        #       directory anyway in the case of the 'dist' operation.
        # TODO: Also zip up package data?

        print('Creating module zipball at "{}" ...'.format(self.zip_file))
        not_zippable = []
        with zipfile.ZipFile(self.zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
          for mod in modules:
            if not mod.check_zippable(self.finder.modules):
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

        copy_modules = not_zippable
        if not_zippable:
          print('Note: There are modules that can not be zipped, they will be copied into the lib/ folder.')

      else:
        copy_modules = modules if self.dist else []

      if copy_modules:
        print('Copying modules to "{}" ...'.format(lib_dir))
        for mod in copy_modules:
          # Copy the module itself.
          src = mod.filename
          dst = os.path.join(lib_dir, mod.relative_filename)
          if mod.type == mod.SRC and not self.srcs:
            src = mod.compiled_file
            dst += 'c'
          elif mod.type == mod.NATIVE:  # TODO: ALso for submodules ..?
            dst = os.path.join(lib_dynload_dir, mod.relative_filename)
          if self.copy_always or nr.fs.compare_timestamp(src, dst):
            nr.fs.makedirs(os.path.dirname(dst))
            shutil.copy(src, dst)

          # Copy package data.
          for name in mod.package_data:
            src = os.path.join(mod.directory, name)
            dst = os.path.join(lib_dir, mod.relative_directory, name)
            copy_files_checked(src, dst, force=self.copy_always)

      if self.dist:
        print('Analyzing native dependencies ...')
        deps = nativedeps.Collection(exclude_system_deps=True)

        # Compile a set of all the absolute native dependencies to exclude.
        stdpath = lambda x: nr.fs.norm(nr.fs.get_long_path_name(x)).lower()
        native_deps_exclude = set()
        for mod in modules:
          native_deps_exclude.update(stdpath(x) for x in mod.native_deps_exclude)

        # Resolve dependencies.
        search_path = deps.search_path
        for name, path in self.python_bins.items():
          dep = deps.add(path, recursive=True)
          dep.name = name
        for mod in modules:
          deps.search_path = list(stream.concat(x.native_deps_path for x in mod.hierarchy_chain())) + search_path
          if mod.type == mod.NATIVE and mod.do_native_deps:
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

        runtime_dir = os.path.join(self.bundle_dir, 'runtime')
        print('Copying Python interpreter and native dependencies to "{}"...'.format(runtime_dir))
        nr.fs.makedirs(runtime_dir)
        for dep in deps:
          if dep.filename and stdpath(dep.filename) not in native_deps_exclude:
            dst = os.path.join(runtime_dir, os.path.basename(dep.name))
            if self.copy_always or nr.fs.compare_timestamp(dep.filename, dst):
              shutil.copy(dep.filename, dst)

    return did_stuff
