
> Note: This package is in the dangerous land of `0.x.y` versions and may be subject to breaking
> changes with minor version increments.

# nr.metaclass

This module provides utilities for Python classes and metaclasses.

* `nr.metaclass.copy` &ndash; Copy a class, while optionally updating some properties
  (for example the base classes).
* `nr.metaclass.deconflict` &ndash; Functions to determine conflicting metaclasses and
  deconflicting them.
* `nr.metaclass.inline` &ndash; Provides the `InlineMetaclassBase`, allowing you to implement
  `__new__()` and `__init__()` of a metaclass in a class through `__metanew__()` and
  `__metainit__()`.

---

<p align="center">Copyright &copy; 2020 Niklas Rosenstein</p>
