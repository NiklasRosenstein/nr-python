# nr.types

[![CircleCI](https://circleci.com/gh/NiklasRosenstein/python-nr.types.svg?style=svg)](https://circleci.com/gh/NiklasRosenstein/python-nr.types)

`nr.types` is a Python library aiming to provide a broad set of common tools
for developing Python applications.

This library is published to [PyPI] and [Conda-forge]. It is compatible with
CPython 2.7 and 3.4+.

  [PyPI]: https://pypi.org/project/nr.types/
  [Conda-forge]: https://github.com/conda-forge/nr.types-feedstock

__Table of Contents__

* `nr.types.abc` &ndash; Alias for `collections.abc` or `collections`.
* `nr.types.collections` &ndash; Additional container data structures.
* `nr.types.generic` &ndash; Write classes with type parameters.
* `nr.types.interface` &ndash; Programming against interfaces in Python,
  inspired by Zope.
* `nr.types.meta` &ndash; Useful metaclasses.
* `nr.types.proxy` &ndash; Eager and lazy object proxies.
* `nr.types.singletons` &ndash; Provides singletons like `NotSet`.
* `nr.types.stream` &ndash; Streaming iterators in Python.
* `nr.types.structured` &ndash; Data-model description library.
* `nr.types.sumtype` &ndash; Allows you to create sumtypes in Python.
* `nr.types.utils` &ndash; More generic utilities.
  * `nr.types.utils.classdef` &ndash; Helpers for writing class definitions.
  * `nr.types.utils.funcdef` &ndash; Helper for writing functions.
  * `nr.types.utils.function` &ndash; Utilities for function objects.
  * `nr.types.utils.module` &ndash; Utilities for module objects.
  * `nr.types.utils.typing` &ndash; Utilities for objects from the `typing` module.

### Installation

    pip install nr.types

### Run Tests

    pip install -e .[test]
    pytest --cov=./src/nr

---

<p align="center">Copyright &copy; Niklas Rosenstein 2019</p>
