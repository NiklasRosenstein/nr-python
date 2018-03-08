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
import os
import sys
from .modules import ModuleFinder


def get_argument_parser(prog=None):
  parser = argparse.ArgumentParser(prog=prog)
  subparser = parser.add_subparsers(dest='command')

  tree = subparser.add_parser('tree', help='Show the import tree of a '
    'Python module or source file.')
  tree.add_argument('module', help='The name of a Python module or path to '
    'a Python source file.')

  dotviz = subparser.add_parser('dotviz', help='Produce a Dotviz graph from '
    'the imports in the specified Python module or source file.')
  dotviz.add_argument('module', help='The name of a Python module or path to '
    'a Python source file.')

  return parser


def main(argv=None, prog=None):
  parser = get_argument_parser(prog)
  args = parser.parse_args(argv)
  if not args.command:
    parser.print_usage()
    return 0
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
