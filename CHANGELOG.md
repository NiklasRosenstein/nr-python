# Changelog

### v2.4.0 (2019-06-25)

* Add `stream.batch()`
* Add `interface.staticattr()`

### v2.3.0 (2019-06-05)

* Fix `Interface` member inheritance if an interface is subclassed
* Add `overrides()` decorator to `nr.types.interface`
* Add `proxy(lazy=False)` parameter
* Removed debug print in `make_proxy_class()`

### v2.2.0 (2019-05-10)

* Rename/restructure `nr.types.local` module
    * Now called `nr.types.proxy`
    * `proxy` class is still pretty much based on `LocalProxy`, not much you
      can do different with this kind of class though
    * Add `make_proxy_class(name, include=None, exclude=None)` function
    * The `nr.types.proxy` module in itself is now callable and returns a
      `proxy` instance
* Add `make_callable` to `nr.types.moduletools`

### v2.1.1 (2019-05-10)

* Remove `Local` and `LocalManager` class from `nr.types.local`, keeping only
  the `LocalProxy` class

### v2.1.0 (2019-05-10)

* Add `CleanRecord.__field_type__` static member which can be overwritten by
  a subclass
* `Field.with_name()` now forwards arbitrary args/kwargs
* Fields can now also be declared as dictionaries in `__fields__`/`__annotations__`
* `ToJSON.to_json()` mixin method now handles mappings and sequences recursively
* Add `nr.types.local` module (vendored from `pallets/werkzeug@0.15.2`,
  licensed BSD-3-Clause, Copyright Pallets 2007)

### v2.0.1 (2019-04-16)

* `nr.types.record`: Fix Python 2 field order

### v2.0.0 (2019-04-16)

* Restructure of the `nr.types` module
* Removed `nr.types.named`
* Updated `nr.types.record` to be much like the old `nr.types.named` and more
* Renamed `nr.types.map` to `nr.types.maps`
* Renamed `nr.types.set` to `nr.types.sets`
* Renamed `nr.types.function` to `nr.types.functools`
* Updated `nr.types.sumtype`
* Added `nr.types.abc`, `nr.types.generic`, `nr.types.moduletools`, `nr.types.stream`
* Added testcases for all modules
