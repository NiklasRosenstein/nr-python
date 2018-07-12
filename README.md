# `nr.fs`

&ndash; Filesystem and path manipulation tools.

> Note: To use the `nr.fs.glob()` function, you need the [glob2] module
> installed. It is not listed an install requirement to this module.

  [glob2]: https://pypi.org/project/glob2/

### Changes

#### v1.0.2

* `get_long_path_name()` returns path as-is on non-NT platforms
* Add `tempfile.encoding` property
* When `tempfile(encoding)` parameter was not specified, its `encoding`
  property will still return the applied text file encoding after it
  has been opened

#### v1.0.1 (2018-07-05)

* Add `nr.fs.isfile_cs()`
* Add `nr.fs.get_long_path_name()`
* Add `namespace_packages` parameter in `setup.py`
