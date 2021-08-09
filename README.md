Monorepository for Python libraries under the `nr` namespace.

[![Build Status](https://drone.niklasrosenstein.com/api/badges/NiklasRosenstein/nr/status.svg)](https://drone.niklasrosenstein.com/NiklasRosenstein/nr)

__A note on versioning__:

All packages that are in `0.X.Y` version should assume that breaking changes are possible
between minor version releases. It is therefore highly recommended that dependencies to
0-major versions are bounded to the next minor version release, eg. `~0.1.2` (`>=0.1.2,<0.2.0`).

## Packages

* [nr.ansiterm](https://pypi.org/project/nr.ansiterm/) &ndash; ANSI terminal colors.
* [nr.caching](https://pypi.org/project/nr.caching/) &ndash; A simple key-value caching API with default implementations for an SQLite3 storage backend and a JSON convenience layer.
* [nr.collections](https://pypi.org/project/nr.collections/) &ndash; Useful container datatypes (ChainDict and OrderedSet).
* [nr.config](https://pypi.org/project/nr.config/) &ndash; Utility library to implement composable YAML configuration files.
* [nr.databind.rest](https://pypi.org/project/nr.databind.rest/) &ndash; Define Type-safe REST API definition and implementation.
* [nr.fs](https://pypi.org/project/nr.fs/) &ndash; Filesystem and path manipulation tools.
* [nr.functional](https://pypi.org/project/nr.functional/) &ndash; Tools for functional programming in Python.
* [nr.markdown](https://pypi.org/project/nr.markdown/) &ndash; Extends the misaka Markdown parser and renderer for some nifty features.
* [nr.metaclass](https://pypi.org/project/nr.metaclass/) &ndash; Metaclass utilities.
* [nr.optional](https://pypi.org/project/nr.optional/) &ndash; Optional type in Python, allow mapping and flat-mapping if you also have nr.stream installed.
* [nr.parsing.core](https://pypi.org/project/nr.parsing.core/) &ndash; A simple API to scan and tokenize text for the purpose of structured language processing.
* [nr.parsing.date](https://pypi.org/project/nr.parsing.date/) &ndash; A fast, regular-expression based library for parsing dates, plus support for ISO 8601 durations.
* [nr.preconditions](https://pypi.org/project/nr.preconditions/) &ndash; Provides simple functions to assert the state of your program.
* [nr.proxy](https://pypi.org/project/nr.proxy/) &ndash; Provides proxy classes that allow accessing objects that are usually only accessible via
function calls as objects directly.
* [nr.pylang.ast](https://pypi.org/project/nr.pylang.ast/) &ndash; Provides utilities for modifying the Python AST.
* [nr.pylang.utils](https://pypi.org/project/nr.pylang.utils/) &ndash; A small collection of utiltiies for Python programming.
* [nr.refreshable](https://pypi.org/project/nr.refreshable/) &ndash; A refreshable is a simple container for a value changing over time.
* [nr.stream](https://pypi.org/project/nr.stream/) &ndash; Use iterators like Java streams.
* [nr.utils.git](https://pypi.org/project/nr.utils.git/) &ndash; A simple wrapper around the Git CLI.
* [nr.utils.io](https://pypi.org/project/nr.utils.io/) &ndash; Collection for IO utilities.
* [nr.utils.ponyorm](https://pypi.org/project/nr.utils.ponyorm/) &ndash; Utilities for working with the Pony ORM framework.
* [nr.utils.process](https://pypi.org/project/nr.utils.process/) &ndash; Utilities for cross-platform process handling and privilege escalation.
* [nr.utils.re](https://pypi.org/project/nr.utils.re/) &ndash; This module provides some utility functions for applying regular expressions.

---

    shut mono status --json --include-config | jq -r '.[] | select(.behind != null) | 
        "* [" + .name + "](https://pypi.org/project/" + .name + "/) &ndash; " 
        + .package.description'
