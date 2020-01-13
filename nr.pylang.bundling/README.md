# nr.bundler

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

PyBundle is a command-line tool to create standalone Python applications. It
aims to be a cross-platform replacement for cx_Freeze and a lightweight
alternative to PyInstaller.

Currently native dependency resolution is only supported on Windows.

#### Hooks

Big Python libraries for which hooks exist only include elements of the module
that are recognized to be necessary. Most of these hooks support command-line
options to enable including the whole library anyway. These options are shown
in parentheses.

* PyQt5 (`--hook-PyQt5:whole`)
* PySide2
* wxPython (`wx`)
* Qt.py (`Qt`)

#### Synopsis

```
$ nr python-bundler --help
usage: nr python-bundler [-h] [--version] [-v] [--flat] [--json]
                         [--json-graph] [--dotviz] [--search SEARCH]
                         [--recursive] [--whitelist GLOB] [--deps]
                         [--package-members] [--nativedeps]
                         [--show-module-path] [--show-hooks-path] [--collect]
                         [--dist] [--entry SPEC] [--resource SRC[:DST]]
                         [--bundle-dir DIRECTORY] [--exclude EXCLUDE]
                         [--no-default-includes] [--no-default-excludes]
                         [--compile-modules] [--zip-modules]
                         [--zip-file ZIP_FILE] [--no-srcs] [--copy-always]
                         [--no-default-module-path] [--module-path PATH]
                         [--no-default-hooks-path] [--hooks-path PATH]
                         [args [args ...]]

Create standalone distributions of Python applications.

positional arguments:
  args                  Additional positional arguments. The interpretation of
                        these arguments depends on the selected operation.

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  -v, --verbose         Increase the log-level from ERROR.
  --flat                Instruct certain operation to produce flat instead of
                        nested output.
  --json                Instruct certain operations to output JSON.
  --json-graph          Instruct certain operations to output JSON Graph.
  --dotviz              Instruct certain operations to output Dotviz.
  --search SEARCH       Instruct certain operations to search for the
                        specified string. Used with --nativedeps
  --recursive           Instruct certain operations to operate recursively.
                        Used with --nativedeps
  --whitelist GLOB      Only search and bundle modules matching the specified
                        glob pattern.

operations (dump):
  --deps                Dump the dependency tree of the specified Python
                        module(s) to stdout and exit.
  --package-members     Dump the members of the specified Python package(s) to
                        stdout and exit.
  --nativedeps          Dump the dependencies of the specified native
                        binary(ies) and exit.
  --show-module-path    Print the module search path to stdout and exit.
  --show-hooks-path     Print the hooks search path to stdout and exit.

operations (build):
  --collect             Collect all modules in the bundle/modules/. This is
                        operation is is automatically implied with the --dist
                        operation.
  --dist                Create a standalone distribution of the Python
                        interpreter. Unless --no-defaults is specified, this
                        will include just the core libraries required by the
                        Python interpreter and a modified site.py module.
                        Additional arguments are treated as modules that are
                        to be included in the distribution.
  --entry SPEC          Create an executable from a Python entrypoint
                        specification and optional arguments in the standalone
                        distribution directory. The created executable will
                        run in console mode unless the spec is prefixed with
                        an @ sign (as in @prog=module:fun).
  --resource SRC[:DST]  Copy thepath(s) to the bundle directory. If DST is not
                        specified, it defaults to res/{srcbasename}/. The path
                        to the res/ directory can be retrieved with
                        `sys.frozen_env["resource_dir"]`.

optional arguments (build):
  --bundle-dir DIRECTORY
                        The name of the directory where collected modules and
                        the standalone Python interpreter be placed. Defaults
                        to bundle/.
  --exclude EXCLUDE     A comma-separated list of modules to exclude. Any sub-
                        modules of the listed package will also be excluded.
                        You can also exact import chains as X->Y where Y is
                        the module imported from X. This argument can be
                        specified multiple times.
  --no-default-includes
                        Do not add default module includes (the Python core
                        library).
  --no-default-excludes
                        Do not add default import excludes.
  --compile-modules     Compile collected Python modules.
  --zip-modules         Zip collected Python modules. Note that modules that
                        are detected to be not supported when zipped will be
                        left out. Must be combined with --dist or --collect.
  --zip-file ZIP_FILE   The output file for --zip-modules.
  --no-srcs             Exclude source files from modules directory or
                        zipfile.
  --copy-always         Always copy files, even if the target file already
                        exists and the timestamp indicates that it hasn't
                        changed.

optional arguments (search):
  --no-default-module-path
                        Ignore the current Python module search path available
                        via sys.path.
  --module-path PATH    Specify an additional path to search for Python
                        modules. Can be comma-separated or specified multiple
                        times.
  --no-default-hooks-path
                        Do not use the default hooks search path for the hooks
                        delivered with PyBundle.
  --hooks-path PATH     Specify an additional path to search for module search
                        hooks. Can be comma-separated or specified multiple
                        times.
```

---

<p align="center">Copyright &copy; 2018 Niklas Rosenstein</p>
