# nr.pybundle

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

PyBundle is an API and command-line tool to collect all dependencies of a
Python application and placing them in a common directory.

#### Project Goals

* Replace cx_Freeze
* Become a lightweight alternative to PyInstaller
* Functional on common platforms (Windows, Linux and macOS)

#### Features

* [x] Create a dependency tree/graph of your Python application with the `tree` or `graph` commands
* [x] Collect all modules in a single directory for distribution with the `collect` command
* [ ] Create a standalone application including Python interpreter and all dependencies with the `standalone` command

#### To do

* The `collect` command should also be able to collect DLL/shared library dependencies of native Python modules (C extensions)
* The `collect` command should accept arguments to search for modules only in a specific list of directories
* The `collect` command should by default exclude Python modules that are imported yet commonly unused in the Python standard library (eg. `pydoc` imported from `pdb`)
* The `collect` command should accept options to ignore `import` statements from within function bodies (on by default, such imports should be explicitly included)
* The `collect` command should be extensible with Python code in order to be able to detect additional Python modules or shared library dependencies that may not be automatically discovered
* The `collect` command needs to take package-data into account and include it in the generated bundle
* The `collect` command should accept an option to include full packages and not just modules that have actually been determined to be imported
* The `collect` command should skip DLLs/shared libraries that are a core part of the OS (eg. `user32.dll` on Windows)
* Support packing binaries with [UPX](https://upx.github.io/)

---

<p align="center">Copyright &copy; 2018 Niklas Rosenstein</p>
