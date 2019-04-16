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

from nr.types import stream
from . import nativedeps, __version__
from .utils import system
from .bundle import DistributionBuilder

import argparse
import json
import logging
import os
import sys


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


def get_argument_parser(prog=None):
  parser = argparse.ArgumentParser(prog=prog, description=main.__doc__, allow_abbrev=False)
  parser.add_argument('args', nargs='*',
    help='Additional positional arguments. The interpretation of these '
         'arguments depends on the selected operation.')

  parser.add_argument('--version', action='version',
    version='nr.pybundle {} ({})'.format(__version__, sys.version))
  parser.add_argument('-v', '--verbose', action='count', default=0,
    help='Increase the log-level from ERROR.')
  parser.add_argument('--flat', action='store_true',
    help='Instruct certain operation to produce flat instead of nested output.')
  parser.add_argument('--json', action='store_true',
    help='Instruct certain operations to output JSON.')
  parser.add_argument('--json-graph', action='store_true',
    help='Instruct certain operations to output JSON Graph.')
  parser.add_argument('--dotviz', action='store_true',
    help='Instruct certain operations to output Dotviz.')
  parser.add_argument('--search',
    help='Instruct certain operations to search for the specified string. '
         'Used with --nativedeps')
  parser.add_argument('--recursive', action='store_true',
    help='Instruct certain operations to operate recursively. '
         'Used with --nativedeps')
  parser.add_argument('--whitelist', action='append', default=[],
    dest='whitelist', metavar='GLOB',
    help='Only search and bundle modules matching the specified glob pattern.')

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
    help='Collect all modules in bundle/lib/. This is operation is '
         'is automatically implied with the --dist operation.')
  group.add_argument('--collect-to', metavar='PATH',
    help='Collect all modules to the specified directory. This argument '
         'cannot be used to alter the bundle\'s lib/ directory. As this '
         'will not create a bundle but simply collect Python modules into '
         'the designated directory, this option can not be combined with '
         '--dist.')
  group.add_argument('--dist', action='store_true',
    help='Create a standalone distribution of the Python interpreter. '
         'Unless --no-defaults is specified, this will include just the '
         'core libraries required by the Python interpreter and a modified '
         'site.py module. Additional arguments are treated as modules that '
         'are to be included in the distribution.')
  group.add_argument('--entry', action='append', default=[], metavar='SPEC',
    help='Create an executable from a Python entrypoint specification '
         'and optional arguments in the standalone distribution directory. '
         'The created executable will run in console mode unless the spec '
         'is prefixed with an @ sign (as in @prog=module:fun).')
  group.add_argument('--resource', action='append', default=[], metavar='SRC[:DST]',
    help='Copy thepath(s) to the bundle directory. If DST is not specified, '
         'it defaults to res/{srcbasename}/. The path to the res/ directory '
         'can be retrieved with `sys.frozen_env["resource_dir"]`.')

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
  args, unknown = parser.parse_known_args(argv)

  if args.verbose == 0:
    level = logging.ERROR
  elif args.verbose == 1:
    level = logging.WARN
  else:
    level = logging.INFO
  logging.basicConfig(level=level)

  hook_options = {}
  for x in unknown:
    if not x.startswith('--hook-'):
      parser.error('unknown option: {}'.format(x))
    if '=' in x:
      key, value = x[7:].partition('=')[::2]
    else:
      key = x[7:]
      value = 'true'
    hook_options[key.lower()] = value

  builder = DistributionBuilder(
    collect = args.collect,
    collect_to = args.collect_to,
    dist = args.dist,
    entries = args.entry,
    resources = args.resource,
    bundle_dir = args.bundle_dir,
    excludes = split_multiargs(args.exclude),
    default_excludes = not args.no_default_excludes,
    includes = split_multiargs(args.args),
    whitelist = split_multiargs(args.whitelist),
    default_includes = not args.no_default_includes,
    compile_modules = args.compile_modules,
    zip_modules = args.zip_modules,
    zip_file = args.zip_file,
    srcs = not args.no_srcs,
    copy_always = args.copy_always,
    module_path = split_multiargs(args.module_path),
    default_module_path = not args.no_default_module_path,
    hooks_path = split_multiargs(args.hooks_path),
    default_hooks_path = not args.no_default_hooks_path,
    hook_options = hook_options
  )

  if args.show_module_path:
    dump_list(builder.finder.path, args)
    return 0

  if args.show_hooks_path:
    dump_list(builder.hook.path, args)
    return 0

  if args.package_members:
    result = {}
    flat = []
    for name in args.args:
      module = builder.finder.find_module(name)
      if not args.json:
        print('{} ({})'.format(module.name, module.type))
      contents = result.setdefault(module.name, [])
      for submodule in stream.chain([module], builder.finder.iter_package_modules(module)):
        data = {'name': submodule.name, 'type': submodule.type, 'filename': submodule.filename}
        contents.append(data)
        flat.append(data)
        if not args.json and submodule != module:
          print('  {} ({})'.format(submodule.name, submodule.type))
    if args.json:
      json.dump(flat if args.flat else result, sys.stdout, indent=2, sort_keys=True)
    return 0

  if args.deps:
    def callback(module, depth):
      print('  ' * depth + '{} ({})'.format(module.name, module.type))
    if args.json or args.dotviz or args.json_graph:
      callback = None
    for name in args.args:
      builder.graph.collect_modules(name, callback=callback)
    if args.json_graph:
      nodes = set()
      graph = {'nodes': [], 'edges': []}
      def mknode(name):
        if name not in nodes:
          graph['nodes'].append({'id': name})
          nodes.add(name)
      def mkedge(a, b):
        mknode(a)
        mknode(b)
        graph['edges'].append({'source': a, 'target': b})
      for mod in builder.graph:
        mknode(mod.name)
        for name in mod.imported_from:
          mkedge(mod.name, name)
      json.dump({'graph': graph}, sys.stdout, indent=2, sort_keys=True)

    """
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
    """
    return 0

  if args.nativedeps:
    # TODO: Dotviz output

    result = {}
    if args.search:
      result[args.search] = []
    for filename in args.args:
      deps = nativedeps.Collection(exclude_system_deps=True)
      deps.add(filename, dependencies_only=True, recursive=args.recursive)
      if args.search:
        for dep in deps:
          if dep.name.lower() == args.search.lower():
            if not args.json:
              print(filename)
            result[args.search].append(filename)
            break
      else:
        result[filename] = []
        if not args.json:
          print(filename)
        for dep in deps:
          dep_filename = nativedeps.resolve_dependency(dep)
          if not args.json:
            print('  {}'.format(dep_filename or dep.name))
          result[filename].append({'name': dep.name, 'filename': dep_filename})
    if args.json:
      json.dump(result, sys.stdout, indent=2, sort_keys=True)
    return 0

  show_usage = not builder.build()
  if show_usage:
    parser.print_usage()
    return 0


if __name__ == '__main__':
  sys.exit(main())
