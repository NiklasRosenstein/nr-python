# nr.pybundle

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

PyBundle is an API and command-line tool to collect all dependencies of a
Python application and placing them in a common directory.

#### Project Goals

* Replace cx_Freeze
* Become a lightweight alternative to PyInstaller
* Functional on common platforms (Windows, Linux and macOS)

#### Synopsis

```
$ nr pybundle --help
usage: nr pybundle [-h] [-v] [--flat] [--json] [--dotviz] [--deps]
                   [--package-members] [--nativedeps] [--show-module-path]
                   [--show-hooks-path] [--collect] [--dist] [--entry SPEC]
                   [--wentry SPEC] [--bundle-dir DIRECTORY]
                   [--exclude EXCLUDE] [--no-default-includes]
                   [--no-default-excludes] [--compile-modules] [--zip-modules]
                   [--zip-file ZIP_FILE] [--no-srcs] [--copy-always]
                   [--sparse] [--no-default-module-path] [--module-path PATH]
                   [--no-default-hooks-path] [--hooks-path PATH]
                   [args [args ...]]

Create standalone distributions of Python applications.

positional arguments:
  args                  Additional positional arguments. The interpretation of
                        these arguments depends on the selected operation.

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         Increase the log-level from ERROR.
  --flat                Instruct certain operation to produce flat instead of
                        nested output.
  --json                Instruct certain operations to output JSON.
  --dotviz              Instruct certain operations to output Dotviz.

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
                        specification in the standalone distribution
                        directory. This executable will run in console mode.
                        This option can be used multiple times and may have
                        comma-separated elements.
  --wentry SPEC         The same as --entry, but the executable will run in
                        GUI mode.

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
  --sparse              Collect modules sparsely, only including package
                        members that appear to actually be used. This affects
                        only Python modules, not package data.

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
