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
import nr.path
import os
import py_compile
import sys
import shutil
import zipfile
from nr.stream import stream
from . import nativedeps
from .modules import ModuleFinder


def get_argument_parser(prog=None):
  class SubParsersAction(argparse._SubParsersAction):
    def add_parser(self, name, **kwargs):
      kwargs.setdefault('add_help', False)
      return super(SubParsersAction, self).add_parser(name, **kwargs)

  parser = argparse.ArgumentParser(prog=prog, add_help=False)
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

  for p in (tree, dotviz, collect):
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
      'defaults to the "modules-compiled" directory in the -D, --dist-dir. '
      'If this option is explicitly specified, it implies -b, --bytecompile.')
  collect.add_argument('-b', '--bytecompile', action='store_true',
    help='Compile the collected Python modules to .pyc files.')
  collect.add_argument('-f', '--force', action='store_true',
    help='Do not copy modules to the dest directory if they seem unchanged '
      'from their timestamp.')
  collect.add_argument('--exclude', action='append', default=[],
    help='A comma-separated list of module names to exclude. Any sub-modules '
      'of the listed package will also be excluded. This argument can be '
      'specified multiple times.')
  collect.add_argument('-z', '--zipmodules', action='store_true',
    help='Create a ZIP file from the modules. If -b, --bytecompile is set '
      'or implied, the compiled modules directory will be zipped.')
  collect.add_argument('-s', '--standalone', action='store_true',
    help='Create a standalone package that includes the Python interpreter.')
  collect.add_argument('-S', '--standalone-dir',
    help='The output directory for the standalone package.')

  return parser


def main(argv=None, prog=None):
  logging.basicConfig(level=logging.INFO)
  parser = get_argument_parser(prog)
  args = parser.parse_args(argv)
  if not args.command:
    parser.print_usage()
    return 0
  args._parser = parser
  globals()['do_' + args.command](args)


_entry_point = lambda: sys.exit(main())


def _iter_modules(module, finder=None):
  if os.sep in module or os.path.isfile(module):
    module, filename = None, module
  else:
    module, filename = module, None
  if not finder:
    finder = ModuleFinder()
  return finder.iter_modules(module, filename)


def do_tree(args):
  for mod in _iter_modules(args.module):
    print('  ' * len(mod.imported_from) + mod.name)


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
  else:
    # -c, --compile-dir implies -b, --bytecompile.
    args.bytecompile = True
  if not args.standalone_dir:
    args.standalone_dir = os.path.join(args.dist_dir, 'package')
  else:
    # -S, --standalone-dir implies -s, --standalone.
    args.standalone = True
  if args.standalone:
    args.bytecompile = True
    args.zipmodules = True

  # Prepare the module finder.
  excludes = list(stream.concat([x.split(',') for x in args.exclude]))
  finder = ModuleFinder(excludes=excludes)

  print('Collecting modules ...')
  seen = set()
  modules = []

  it = _iter_modules(args.module, finder)
  it = stream.chain(it, *[finder.iter_modules(x) for x in args.include])
  for mod in it:
    if mod.type == mod.BUILTIN: continue
    if mod.name in seen: continue
    seen.add(mod.name)
    if mod.type == mod.NOTFOUND:
      print('  warning: module not found: {!r}'.format(mod.name))
      continue
    modules.append(mod)

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
    if not args.force and not nr.path.compare_timestamp(mod.filename, dest):
      unchanged += 1
      continue
    nr.path.makedirs(os.path.dirname(dest))
    shutil.copy(mod.filename, dest)

  if unchanged:
    print('  note: Skipped {} modules that seem unchanged.'.format(unchanged))

  if args.bytecompile and compile_files:
    print('Byte-compiling {} files to "{}" ...'.format(len(compile_files), args.compile_dir))
    unchanged = 0
    for src, dst in compile_files:
      if not args.force and not nr.path.compare_timestamp(src, dst):
        unchanged += 1
        continue
      nr.path.makedirs(os.path.dirname(dst))
      py_compile.compile(src, dst, doraise=True)

    if unchanged:
      print('  note: Skipped {} modules that seem unchaged.'.format(unchanged))

  if args.bytecompile and copy_files:
    print('Copying remaining {} non-source file(s) to "{}" ...'.format(len(copy_files), args.compile_dir))
    unchanged = 0
    for src, dst in copy_files:
      if not args.force and not nr.path.compare_timestamp(src, dst):
        unchanged += 1
        continue
      nr.path.makedirs(os.path.dirname(dst))
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
        copy_files.append(mod.filename)

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
      if not args.force and not nr.path.compare_timestamp(src, dst):
        continue
      nr.path.makedirs(os.path.dirname(dst))
      shutil.copy(src, dst)

    shutil.copy(zipball, os.path.join(args.standalone_dir, 'libs.zip'))


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
