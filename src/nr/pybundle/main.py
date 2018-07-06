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

from distlib.scripts import ScriptMaker
from nr.stream import stream
from . import nativedeps
from .modules import ModuleInfo, ModuleFinder, core_libs, common_excludes

import argparse
import json
import logging
import nr.fs
import os
import py_compile
import re
import sys
import shutil
import zipfile

logger = logging.getLogger(__name__)

SCRIPT_TEMPLATE = '''
# -*- coding: utf-8 -*-
if __name__ == '__main__':
  import sys
  module = __import__('%(module)s')
  for name in '%(module)s'.split('.')[1:]:
    module = getattr(module, name)
  func = getattr(module, '%(func)s')
  sys.exit(func())
'''.strip()


def split_multiargs(value):
  if not value:
    return []
  return list(stream.concat([x.split(',') for x in value]))


def dump_list(lst, args):
  if args.json:
    json.dump(lst, sys.stdout, indent=2)
    print()
  else:
    for x in lst:
      print(x)


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


def make_script(python_executable, dirname, spec, gui=False):
  if not re.match('^[\w_\.\-]+=([\w_\.]+):[\w_\.]+$', spec):
    raise ValueError('invalid entrypoint spec: {!r}'.format(spec))
  maker = ScriptMaker(None, dirname)
  maker.script_template = SCRIPT_TEMPLATE
  maker.executable = python_executable
  maker.variants = set([''])
  maker.make(spec, options={'gui': gui})


def get_argument_parser(prog=None):
  parser = argparse.ArgumentParser(prog=prog, description=main.__doc__)
  parser.add_argument('args', nargs='*',
    help='Additional positional arguments. The interpretation of these '
         'arguments depends on the selected operation.')

  parser.add_argument('-v', '--verbose', action='count', default=0,
    help='Increase the log-level from ERROR.')
  parser.add_argument('--flat', action='store_true',
    help='Instruct certain operation to produce flat instead of nested output.')
  parser.add_argument('--json', action='store_true',
    help='Instruct certain operations to output JSON.')
  parser.add_argument('--dotviz', action='store_true',
    help='Instruct certain operations to output Dotviz.')

  group = parser.add_argument_group('operations (dump)')
  group.add_argument('--deps', action='store_true',
    help='Dump the dependency tree of the specified Python module(s) to '
         'stdout and exit.')
  group.add_argument('--package-members', action='store_true',
    help='Dump the members of the specified Python package(s) to stdout '
         'and exit.')
  group.add_argument('--nativedeps', action='store_true',
    help='Dump the dependencies of the specified native binary(ies) and exit.')
  group.add_argument('--show-module-path', action='store_true',
    help='Print the module search path to stdout and exit.')
  group.add_argument('--show-hooks-path', action='store_true',
    help='Print the hooks search path to stdout and exit.')

  group = parser.add_argument_group('operations (build)')
  group.add_argument('--collect', action='store_true',
    help='Collect all modules in the bundle/modules/. This is operation is '
         'is automatically implied with the --dist operation.')
  group.add_argument('--dist', action='store_true',
    help='Create a standalone distribution of the Python interpreter. '
         'Unless --no-defaults is specified, this will include just the '
         'core libraries required by the Python interpreter and a modified '
         'site.py module. Additional arguments are treated as modules that '
         'are to be included in the distribution.')
  group.add_argument('--entry', action='append', default=[], metavar='SPEC',
    help='Create an executable from a Python entrypoint specification in '
         'the standalone distribution directory. This executable will run '
         'in console mode. This option can be used multiple times and may '
         'have comma-separated elements.')
  group.add_argument('--wentry', action='append', default=[], metavar='SPEC',
    help='The same as --entry, but the executable will run in GUI mode.')

  group = parser.add_argument_group('optional arguments (build)')
  group.add_argument('--bundle-dir', metavar='DIRECTORY', default='bundle',
    help='The name of the directory where collected modules and the '
         'standalone Python interpreter be placed. Defaults to bundle/.')
  group.add_argument('--exclude', action='append', default=[],
    help='A comma-separated list of modules to exclude. Any sub-modules '
         'of the listed package will also be excluded. You can also exact '
         'import chains as X->Y where Y is the module imported from X. This '
         'argument can be specified multiple times.')
  group.add_argument('--no-default-includes', action='store_true',
    help='Do not add default module includes (the Python core library).')
  group.add_argument('--no-default-excludes', action='store_true',
    help='Do not add default import excludes.')
  group.add_argument('--compile-modules', action='store_true',
    help='Compile collected Python modules.')
  group.add_argument('--zip-modules', action='store_true',
    help='Zip collected Python modules. Note that modules that are detected '
         'to be not supported when zipped will be left out. Must be combined '
         'with --dist or --collect.')
  group.add_argument('--zip-file',
    help='The output file for --zip-modules.')
  group.add_argument('--no-srcs', action='store_true',
    help='Exclude source files from modules directory or zipfile.')
  group.add_argument('--copy-always', action='store_true',
    help='Always copy files, even if the target file already exists and the '
         'timestamp indicates that it hasn\'t changed.')
  group.add_argument('--sparse', action='store_true',
    help='Collect modules sparsely, only including package members that '
         'appear to actually be used. This affects only Python modules, not '
         'package data.')

  group = parser.add_argument_group('optional arguments (search)')
  group.add_argument('--no-default-module-path', action='store_true',
    help='Ignore the current Python module search path available via sys.path.')
  group.add_argument('--module-path', action='append', default=[], metavar='PATH',
    help='Specify an additional path to search for Python modules. Can be '
         'comma-separated or specified multiple times.')
  group.add_argument('--no-default-hooks-path', action='store_true',
    help='Do not use the default hooks search path for the hooks delivered '
         'with PyBundle.')
  group.add_argument('--hooks-path', action='append', default=[], metavar='PATH',
    help='Specify an additional path to search for module search hooks. Can '
         'be comma-separated or specified multiple times.')

  return parser


def main(argv=None, prog=None):
  """
  Create standalone distributions of Python applications.
  """

  parser = get_argument_parser(prog)
  args = parser.parse_args(argv)

  if args.verbose == 0:
    level = logging.ERROR
  elif args.verbose == 1:
    level = logging.WARN
  else:
    level = logging.INFO
  logging.basicConfig(level=level)

  finder = ModuleFinder(excludes=common_excludes)
  if args.no_default_excludes:
    finder.excludes = []
  if args.no_default_module_path:
    finder.path = []
  else:
    finder.path.insert(0, os.getcwd())
  if args.no_default_hooks_path:
    finder.hooks.search_path = []
  finder.path += split_multiargs(args.module_path)
  finder.hooks.search_path += split_multiargs(args.hooks_path)
  finder.excludes += split_multiargs(args.exclude)

  if args.show_module_path:
    dump_list(finder.path, args)
    return 0

  if args.show_hooks_path:
    dump_list(finder.hooks.search_path, args)
    return 0

  if args.package_members:
    result = {}
    for name in args.args:
      module = finder.find_module(name)
      if not args.json:
        print('{} ({})'.format(module.name, module.type))
      contents = result.setdefault(module.name, {})
      for submodule in stream.chain([module], finder.iter_package_modules(module)):
        contents[submodule.name] = {'type': submodule.type, 'filename': submodule.filename}
        if not args.json and submodule != module:
          print('  {} ({})'.format(submodule.name, submodule.type))
    if args.json:
      json.dump(result, sys.stdout, indent=2, sort_keys=True)
    return 0

  if args.deps:
    # TODO: Dotviz output
    result = []
    current = []
    flat = []
    if args.flat:
      show = lambda mod: print('{} ({})'.format(mod.name, mod.type))
    else:
      show = lambda mod: print('  ' * len(mod.imported_from) + '{} ({})'.format(mod.name, mod.type))
    for name in args.args:
      module = finder.find_module(name)
      for module in finder.iter_modules(module, recursive=True):
        if not args.json: show(module)
        data = {'name': module.name, 'type': module.type, 'filename': module.filename}
        if args.flat:
          flat.append(data)
        else:
          assert len(module.imported_from) <= len(current)+1
          data['imports'] = []
          current = current[:len(module.imported_from)]
          if current:
            current[-1]['imports'].append(data)
          else:
            result.append(data)
          current.append(data)
    if args.json:
      json.dump(flat if args.flat else result, sys.stdout, indent=2, sort_keys=True)
    return 0

  if args.nativedeps:
    # TODO: Dotviz output
    # TODO: Recursive dependency resolution (with an option?)
    result = {}
    for filename in args.args:
      deps = nativedeps.get_dependencies(filename)
      if not args.json:
        print(filename)
      result[filename] = []
      for dep in deps:
        dep_filename = nativedeps.resolve_dependency(dep)
        if not args.json:
          print('  {}'.format(dep_filename or dep.name))
        result[filename].append({'name': dep.name, 'filename': dep_filename})
    if args.json:
      json.dump(result, sys.stdout, indent=2, sort_keys=True)
    return 0

  if args.entry or args.wentry:
    python_executable = os.path.join('runtime', os.path.basename(sys.executable))
    for spec in split_multiargs(args.entry):
      make_script(python_executable, args.bundle_dir, spec, gui=False)
    for spec in split_multiargs(args.wentry):
      make_script(python_executable, args.bundle_dir, spec, gui=True)

  if args.dist or args.collect:
    if args.no_srcs and not args.compile_modules:
      parser.error('remove --no-srcs or add --compile-modules')

    print('Resolving dependencies ...')
    modules = [] if args.no_default_includes else list(core_libs)
    modules += args.args
    finder.find_modules(modules, sparse=args.sparse)
    finder.finalize()

    notfound = 0
    modules = []
    for mod in finder.modules.values():
      if mod.type == mod.NOTFOUND:
        logger.warn('Module could not be found: {}'.format(mod.name))
        notfound += 1
      elif mod.type != mod.BUILTIN:
        modules.append(mod)
    if notfound != 0:
      logger.error('{} modules could not be found.'.format(notfound))
      logger.error("But do not panic, most of them are most likely imports "
                   "that are platform dependent or member imports.")
      logger.error('Increase the verbosity with -v, --verbose for details.')

    lib_dir = os.path.join(args.bundle_dir, 'lib')
    if args.zip_modules:
      compile_dir = os.path.join(args.bundle_dir, '.compile-cache')
    else:
      compile_dir = lib_dir

    if args.compile_modules and modules:
      print('Compiling modules in "{}" ...'.format(compile_dir))
      for mod in modules:
        if mod.type == mod.SRC:
          dst = os.path.join(compile_dir, mod.relative_filename + 'c')
          mod.compiled_file = dst
          if args.copy_always or nr.fs.compare_timestamp(mod.filename, dst):
            nr.fs.makedirs(os.path.dirname(dst))
            py_compile.compile(mod.filename, dst, doraise=True)

    if args.zip_modules and modules:
      if not args.zip_file:
        args.zip_file = os.path.join(args.bundle_dir, 'libs.zip')

      # TODO: Exclude core modules that must be copied to the lib/
      #       directory anyway in the case of the 'dist' operation.
      # TODO: Also zip up package data?

      print('Creating module zipball at "{}" ...'.format(args.zip_file))
      not_zippable = []
      with zipfile.ZipFile(args.zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for mod in modules:
          if not mod.check_zippable(finder.modules):
            not_zippable.append(mod)
            continue

          if mod.type == mod.SRC:
            files = []
            if not args.no_srcs:
              files.append((mod.relative_filename, mod.filename))
            if args.compile_modules:
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
      copy_modules = modules if args.dist else []

    if copy_modules:
      print('Copying modules to "{}" ...'.format(lib_dir))
      for mod in copy_modules:
        # Copy the module itself.
        src = mod.filename
        dst = os.path.join(lib_dir, mod.relative_filename)
        if mod.type == mod.SRC and args.no_srcs:
          src = mod.compiled_file
          dst += 'c'
        if args.copy_always or nr.fs.compare_timestamp(src, dst):
          nr.fs.makedirs(os.path.dirname(dst))
          shutil.copy(src, dst)

        # Copy package data.
        for name in mod.package_data:
          src = os.path.join(mod.directory, name)
          dst = os.path.join(lib_dir, mod.relative_directory, name)
          copy_files_checked(src, dst, force=args.copy_always)

    if args.dist:
      print('Analyzing native dependencies ...')
      deps = nativedeps.Collection(exclude_system_deps=True)

      # Concatenate all override native search paths. They take
      # priority over the default search path.
      # Also compile a set of all the absolute native dependencies to
      # exclude.
      stdpath = lambda x: nr.fs.norm(nr.fs.get_long_path_name(x)).lower()
      native_deps_exclude = set()
      for mod in modules:
        deps.search_path = mod.native_deps_path + deps.search_path
        native_deps_exclude.update(stdpath(x) for x in mod.native_deps_exclude)

      # Resolve dependencies.
      deps.add(sys.executable, recursive=True)
      deps.add(os.path.join(os.path.dirname(sys.executable), os.path.basename(sys.executable).replace('python', 'pythonw')), recursive=True)
      for mod in modules:
        if mod.type == mod.NATIVE and mod.do_native_deps:
          deps.add(mod.filename, dependencies_only=True, recursive=True)

      # Warn about dependencies that can not be found.
      notfound = 0
      for dep in deps:
        if not dep.filename:
          notfound += 1
          logger.warn('Native dependency could not be found: {}'.format(dep.name))
      if notfound != 0:
        logger.error('{} native dependencies could not be found.'.format(notfound))

      runtime_dir = os.path.join(args.bundle_dir, 'runtime')
      print('Copying Python interpreter and native dependencies to "{}"...'.format(runtime_dir))
      nr.fs.makedirs(runtime_dir)
      for dep in deps:
        if dep.filename and stdpath(dep.filename) not in native_deps_exclude:
          dst = os.path.join(runtime_dir, os.path.basename(dep.filename))
          if args.copy_always or nr.fs.compare_timestamp(dep.filename, dst):
            shutil.copy(dep.filename, dst)


if __name__ == '__main__':
  sys.exit(main())
