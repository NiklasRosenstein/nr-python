# Python Bundler

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Bundler is a tool for collecting all modules used by a Python package and
placing them in one common directory. Its aim is to follow into cx_Freeze's
footsteps and to offer a simpler (if not as elaborate) solution to PyInstaller.

### Roadmap

1. Place all Python modules in one common directory
2. Option to bytecompile all modules
3. Skip modules imported but commonly unused by the Python standard library
  (for example `pdb` import `pydoc` which in turn imports the whole `email`
  package, however in 99% of the cases we can skip the `pydoc` package when
  it is imported from `pdb`)
4. Ability to create a standalone application with Python interpreter binaries
5. Ability to create a single executable from the bundled application

---

<p align="center">Copyright &copy; 2018 Niklas Rosenstein</p>
