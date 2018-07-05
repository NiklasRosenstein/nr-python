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

import argparse
import logging
import nr.fs
import os
import py_compile
import re
import sys
import shutil
import zipfile
from distlib.scripts import ScriptMaker
from nr.stream import stream
from . import nativedeps
from .modules import ModuleFinder


include_defaults = ['abc', 'codecs', 'encodings+', 'os', 'site']
exclude_defaults = ['heapq->doctest', 'pickle->doctest', '_sitebuiltins->pydoc']


def get_argument_parser(prog=None):
  class SubParsersAction(argparse._SubParsersAction):
    def add_parser(self, name, **kwargs):
      kwargs.setdefault('add_help', False)
      return super(SubParsersAction, self).add_parser(name, **kwargs)

  parser = argparse.ArgumentParser(prog=prog, add_help=False)
  parser.add_argument('-v', '--verbose', action='store_true')
  parser.register('action', 'parsers', SubParsersAction)
  subparser = parser.add_subparsers(dest='command')

  collect = subparser.add_parser('collect', help='Collect all Python modules '
    'in a directory.')
  help = subparser.add_parser('help', help='Print this help information.')
  dotviz = subparser.add_parser('dotviz', help='Produce a Dotviz graph from '
    'the imports in the specified Python module or source file.')
  tree = subparser.add_parser('tree', help='Show the import tree of a '
    'Python module or source file.')

  help.add_argument('help_command', nargs='?', help='The command to show '
    'the help for.')

  for p in (tree, dotviz):
    p.add_argument('module', help='The name of a Python module or path to '
      'a Python source file.')

  collect.add_argument('include', nargs='*', help='The name of additional '
    'Python modules to include.')
  collect.add_argument('-D', '--dist-dir', metavar='DIRECTORY',
    help='The name of the distribution directory. This is only used to alter '
      'the prefix of the default output directories. Defaults to "dist".')
  collect.add_argument('-d', '--collect-dir', metavar='DIRECTORY',
    help='The name of the directory where the modules will be collected. If '
      'this is not specified, it will default to the "modules" directory in '
      'the -D, --dist-dir.')
  collect.add_argument('-c', '--compile-dir', metavar='DIRECTORY',
    help='The name of the directory where the byte-compiled and native '
      'Python modules will be placed in. If this is not specified, it '
      'defaults to the "modules-compiled" directory in the -D, --dist-dir.')
  collect.add_argument('-b', '--bytecompile', action='store_true', default=None,
    help='Compile the collected Python modules to .pyc files.')
  collect.add_argument('--no-bytecompile', action='store_false', dest='bytecompile',
    help='Turn off byte compilation, use if --bytecompile would otherwise be '
      'implied by another option.')
  collect.add_argument('-f', '--force', action='store_true',
    help='Do not copy modules to the dest directory if they seem unchanged '
      'from their timestamp.')
  collect.add_argument('--exclude', action='append', default=[],
    help='A comma-separated list of module names to exclude. Any sub-modules '
      'of the listed package will also be excluded. This argument can be '
      'specified multiple times. A module name may also include a specific '
      'import from a specific module that should be ignored in the form of '
      'X->Y.')
  collect.add_argument('-z', '--zipmodules', action='store_true',
    help='Create a ZIP file from the modules. If -b, --bytecompile is set '
      'or implied, the compiled modules directory will be zipped.')
  collect.add_argument('-s', '--standalone', action='store_true',
    help='Create a standalone package that includes the Python interpreter. '
      'This implies the --bytecompile option. Use --no-bytecompile to '
      'turn off this implication.')
  collect.add_argument('-S', '--standalone-dir',
    help='The output directory for the standalone package.')
  collect.add_argument('--whole-package', action='store_true',
    help='Collect encountered packages as a whole. While this option is '
      'turned on, you can turn the behavior off for certain packages by '
      'adding a - (minus) to the module-name in the command-line. You can '
      'also leave this option off and turn it on for a specific package by '
      'adding a + (plus) to the module-name.')
  collect.add_argument('--no-srcs', action='store_true',
    help='Do not include source files in the lib/ directory of the '
      'standalone package.')
  collect.add_argument('-e', '--entry', dest='entrypoints', action='append',
    default=None,
    help='Create an application entry point. Must be of the format '
      'name=module:func.')
  collect.add_argument('--no-defaults', action='store_true',
    help='Do not automatically include core packages that are required to '
      'run the Python interpreter.')

  return parser


def main(argv=None, prog=None):
  parser = get_argument_parser(prog)
  args = parser.parse_args(argv)
  if not args.command:
    parser.print_usage()
    return 0
  args._parser = parser
  logging.basicConfig(level=logging.INFO if args.verbose else logging.WARN)
  globals()['do_' + args.command](args)


_entry_point = lambda: sys.exit(main())


def _iter_modules(arg, finder=None):
  if os.sep in arg or os.path.isfile(arg):
    module_name, filename = None, arg
  else:
    module_name, filename = arg, None
  if not finder:
    finder = ModuleFinder()

  if module_name:
    module = finder.find_module(module_name)
    if not module:
      raise RuntimeError('module not found: {}'.format(module_name))
  else:
    module = ModuleInfo('__main__', filename, ModuleInfo.SRC)

  yield module
  yield from finder.iter_modules(module)


def copy_directory(src, dst, force=False):
  """
  Copies the contents of directory *src* into *dst* recursively. Files that
  already exist in *dst* will be timestamp-compared to avoid unnecessary
  copying, unless *force* is specified.

  Returns the number the total number of files and the number of files
  copied.
  """

  total_files = 0
  copied_files = 0

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


def parse_package_spec(spec, collect_whole, collect_sparse):
  if spec[-1] in '+-':
    spec, mode = spec[:-1], spec[-1]
    {'+': collect_whole, '-': collect_sparse}[mode].add(spec)
  return spec


def do_tree(args):
  for mod in _iter_modules(args.module):
    print('  ' * len(mod.imported_from) + mod.name, '({})'.format(mod.type))


def do_dotviz(args):
  edges = set()
  for mod in _iter_modules(args.module):
    if not mod.imported_from: continue
    edges.add((mod.name, mod.imported_from[0]))
  print('digraph {')
  for a, b in edges:
    print('  "{}" -> "{}";'.format(a, b))
  print('}')


def do_collect(args):
  if not args.dist_dir:
    args.dist_dir = 'dist'
  if not args.collect_dir:
    args.collect_dir = os.path.join(args.dist_dir, 'modules')
  if not args.compile_dir:
    args.compile_dir = os.path.join(args.dist_dir, 'modules-compiled')
  if not args.standalone_dir:
    args.standalone_dir = os.path.join(args.dist_dir, 'package')
  if args.standalone and args.bytecompile is None:
    args.bytecompile = True
  if args.bytecompile is None:
    args.bytecompile = False
  if args.entrypoints is None:
    args.entrypoints = []
  for entry in args.entrypoints:
    match = re.match('^[\w_\.\-]+=([\w_\.]+):[\w_\.]+$', entry)
    if not match:
      args._parser.error('invalid entrypoint specification: {}'.format(entry))
    args.include.append(match.group(1))

  if not args.no_defaults:
    if args.entrypoints:
      args.include.append('runpy')
    args.include += include_defaults
    args.exclude += exclude_defaults

  # Prepare the module finder.
  excludes = list(stream.concat([x.split(',') for x in args.exclude]))
  finder = ModuleFinder(excludes=excludes)

  print('Collecting modules ...')
  seen = set()
  modules = []
  collect_whole = set()
  collect_sparse = set()
  for i, module in enumerate(args.include):
    args.include[i] = parse_package_spec(module, collect_whole, collect_sparse)
  it = stream.chain(*[_iter_modules(x, finder) for x in args.include])
  for mod in it:
    if mod.type == mod.BUILTIN: continue
    if mod.name in seen: continue
    seen.add(mod.name)
    if mod.type == mod.NOTFOUND:
      print('  warning: module not found: {!r}'.format(mod.name))
      continue
    modules.append(mod)

    if args.whole_package or (mod.name in collect_whole and not mod.name in collect_sparse):
      for submod in finder.iter_package_modules(mod):
        if submod.name in seen: continue
        seen.add(submod.name)
        modules.append(submod)

  print('Copying {} modules to "{}" ...'.format(len(modules), args.collect_dir))
  unchanged = 0
  compile_files = []
  copy_files = []
  for mod in modules:
    dest = os.path.join(args.collect_dir, mod.relative_filename)
    if mod.type == mod.SRC:
      compile_files.append((dest, os.path.join(args.compile_dir, mod.relative_filename) + 'c'))
    else:
      copy_files.append((dest, os.path.join(args.compile_dir, mod.relative_filename)))
    if not args.force and not nr.fs.compare_timestamp(mod.filename, dest):
      unchanged += 1
      continue
    nr.fs.makedirs(os.path.dirname(dest))
    shutil.copy(mod.filename, dest)

  if unchanged:
    print('  note: Skipped {} modules that seem unchanged.'.format(unchanged))

  if args.bytecompile and compile_files:
    print('Byte-compiling {} files to "{}" ...'.format(len(compile_files), args.compile_dir))
    unchanged = 0
    for src, dst in compile_files:
      if not args.force and not nr.fs.compare_timestamp(src, dst):
        unchanged += 1
        continue
      nr.fs.makedirs(os.path.dirname(dst))
      py_compile.compile(src, dst, doraise=True)

    if unchanged:
      print('  note: Skipped {} modules that seem unchaged.'.format(unchanged))

  if args.bytecompile and copy_files:
    print('Copying remaining {} non-source file(s) to "{}" ...'.format(len(copy_files), args.compile_dir))
    unchanged = 0
    for src, dst in copy_files:
      if not args.force and not nr.fs.compare_timestamp(src, dst):
        unchanged += 1
        continue
      nr.fs.makedirs(os.path.dirname(dst))
      shutil.copy(src, dst)

    if unchanged:
      print('  note: Skipped {} files that seem unchaged.'.format(unchanged))

  if args.zipmodules:
    if args.bytecompile:
      base_dir = args.compile_dir
    else:
      base_dir = args.collect_dir
    filename = base_dir + '.zip'
    print('Creating {} archive "{}" ...'.format(
      'dist' if args.bytecompile else 'source', os.path.basename(filename)))
    with zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
      # TODO: Also include package data files.
      for src, pyc in compile_files:
        src = pyc if args.bytecompile else src
        arcname = os.path.relpath(src, base_dir).replace(os.sep, '/')
        zipf.write(src, arcname)
    zipball = filename

  if args.standalone:
    copy_files = [sys.executable]

    print('Analyzing C-extensions and Python executable ...')
    shared_deps = nativedeps.get_dependencies(sys.executable)
    for mod in modules:
      if mod.type == mod.NATIVE:
        shared_deps += nativedeps.get_dependencies(mod.filename)
        #copy_files.append(mod.filename)

    print('Resolving shared dependencies ...')
    deps_mapping = {}
    for dep in shared_deps:
      if dep.name not in deps_mapping:
        filename = nativedeps.resolve_dependency(dep)
        deps_mapping[dep.name] = filename
        if not filename:
          print('  warning: Could not resolve "{}"'.format(dep.name))
        else:
          copy_files.append(filename)

    print('Creating standalone package ...')
    for src in copy_files:
      dst = os.path.join(args.standalone_dir, 'runtime', os.path.basename(src))
      if not args.force and not nr.fs.compare_timestamp(src, dst):
        continue
      nr.fs.makedirs(os.path.dirname(dst))
      shutil.copy(src, dst)

    if args.zipmodules:
      print('  Copying zipped modules ...')
      shutil.copy(zipball, os.path.join(args.standalone_dir, 'libs.zip'))
      # TODO: We need to copy at least some basic files to the standalone's
      #       lib/ directory, including at least the abc, codecs, encodings,
      #       os and site modules.
      #       The site module must be altered so that there is a zipimporter
      #       for `libs.zip`.
      print('  [TODO]: Add core Python modules to lib/ directory ...')
      nr.fs.makedirs(os.path.join(args.standalone_dir, 'lib'))
      with open(os.path.join(args.standalone_dir, 'lib', 'os.py'), 'w') as fp:
        fp.write('# TODO: Standard os module here ...')
      with open(os.path.join(args.standalone_dir, 'lib', 'site.py'), 'w') as fp:
        fp.write('# TODO: Created zipimporter for libs.zip')
    else:
      if not args.no_srcs:
        print('  Copying module sources ...')
        copy_directory(args.collect_dir, os.path.join(args.standalone_dir, 'lib'))
      if args.bytecompile:
        print('  Copying compiled modules ...')
        copy_directory(args.compile_dir, os.path.join(args.standalone_dir, 'lib'))

    for entry in args.entrypoints:
      import textwrap
      maker = ScriptMaker(None, args.standalone_dir)
      maker.script_template = textwrap.dedent('''
        # -*- coding: utf-8 -*-
        if __name__ == '__main__':
          import sys
          module = __import__('%(module)s', fromlist=[None])
          func = getattr(module, '%(func)s')
          sys.exit(func())
        ''').strip()
      maker.executable = os.path.join('runtime', os.path.basename(sys.executable))
      maker.variants = set([''])
      maker.make(entry)

  print('Done.')


def do_help(args):
  parser = args._parser
  if parser.description:
    print(parser.description)

  subparser_actions = [action for action in parser._actions
                       if isinstance(action, argparse._SubParsersAction)]

  if args.help_command:
    found = False
    for action in subparser_actions:
      for choice in action._choices_actions:
        if choice.dest == args.help_command:
          action._name_parser_map[choice.dest].print_help()
          found = True
          break
    if not found:
      parser.error('{!r} is not a command'.format(args.help_command))
    return 0
  else:
    parser.print_usage()
    print('\ncommands:')
    for action in subparser_actions:
      for choice in action._choices_actions:
        print('  {:<19} {}'.format(choice.dest, choice.help))


if __name__ == '__main__':
  sys.exit(main())
