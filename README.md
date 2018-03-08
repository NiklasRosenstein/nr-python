# Python Bundler

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Bundler is a tool for collecting all modules used by a Python package and
placing them in one common directory. Its goal is to be a better replacement
for cx_Freeze that should work on all common platforms (Windows, Linux, macOS).

__Features__

* [x] Create a dependency tree/graph of your Python application with
  the `tree` or `graph` commands.
* [x] Collect all modules in a single directory for distribution with the
  `collect` command.
* [ ] Create a standalone application including Python interpreter and all
  dependencies with the `standalone` command.

__To do__

* The `collect` command should be able to accept additional module names for
  explicit inclusion in the collection.
* The `collect` command should also be able to collect dependencies of native
  Python modules (C extensions).
* The `collect` command should accept arguments to exclude certain modules
  when they are encountered.
* The `collect` command should accept arguments to search for modules only
  in a specific list of directories
* The `collect` command should accept options to byte-compile all collected
  modules to a separate directory.
* The `collect` command should by default exclude Python modules that are
  imported yet commonly unused in the Python standard library (eg. `pydoc`
  imported from `pdb`).
* The `collect` command should accept options to ignore `import` statements
  from within function bodies (on by default, such imports should be
  explicitly included).
* The `collect` command should be extensible with Python code in order to
  be able to detect additional Python modules or shared library dependencies
  that may not be automatically discovered.

---

<p align="center">Copyright &copy; 2018 Niklas Rosenstein</p>
