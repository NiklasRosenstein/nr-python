
> Note: This package is in the dangerous land of `0.x.y` versions and may be subject to breaking
> changes with minor version increments.

# nr.utils.re

This module provides some utility functions for applying regular expressions.

## Contents

* `match_all(expr, string)`: Matches *expr* from the start of *string* and expects that it can be
  matched throughout. If it fails to consume the full string, a `MatchAllError` will be raised.
  (Note that this exception class is also accessible as `match_all.Error`).

---

<p align="center">Copyright &copy; 2020 Niklas Rosenstein</p>
