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

import argparse
import nr.path
import os
import sys
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

  collect.add_argument('-D', '--dist-directory', metavar='DIRECTORY',
    default='dist/modules', help='The name of the output directory (default: '
      'dist/modules)')
  collect.add_argument('-f', '--force', action='store_true', help='Do not '
    'copy modules to the dest directory if they seem unchanged (from the file '
    'timestamp).')

  return parser


def main(argv=None, prog=None):
  parser = get_argument_parser(prog)
  args = parser.parse_args(argv)
  if not args.command:
    parser.print_usage()
    return 0
  args._parser = parser
  globals()['do_' + args.command](args)


_entry_point = lambda: sys.exit(main())


def _iter_modules(module):
  if os.sep in module or os.path.isfile(module):
    module, filename = None, module
  else:
    module, filename = module, None
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
  import shutil
  nr.path.makedirs(args.dist_directory)

  print('Collecting modules ...')
  seen = set()
  modules = []
  for mod in _iter_modules(args.module):
    if mod.type == mod.BUILTIN: continue
    if mod.name in seen: continue
    seen.add(mod.name)
    if mod.type == mod.NOTFOUND:
      print('  warning: module not found: {!r}'.format(mod.name))
      continue
    modules.append(mod)

  print('Copying {} modules to "{}" ...'.format(len(modules), args.dist_directory))
  unchanged = 0
  for mod in modules:
    dest = os.path.join(args.dist_directory, mod.relative_filename)
    if not args.force and not nr.path.compare_timestamp(mod.filename, dest):
      unchanged += 1
      continue
    nr.path.makedirs(os.path.dirname(dest))
    shutil.copy(mod.filename, dest)

  if unchanged:
    print('  note: Skipped {} modules that seem unchanged.'.format(unchanged))

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
