# Changelog

### v2.5.1 @unreleased

* Fixed unpacking `MethodType` in `Implementation.__metanew__()`
  * This error would surface when using a `@classmethod` in an interface
  * Added a testcase for this part of the metaclass that checks if the
    implementation satisfies the interfaces

### v2.5.0 (2019-07-19)

* Updated `nr.types.interface`
  * Added `Attribute(default)` parameter and `default` member
  * Added `Attribute(static)` parameter and `static` member
  * Added `Attribute.make_default()` parameter and `static` member
  * Added `Method(static)` parameter and `static` member
  * Added internal `Decoration()` class which is now used instead of
    setting members on the functions decorated with `@default`, `@final`,
    `@override` and `@overrides()`
  * Changed `staticattr()`, now returns an `Attribute` instance
    with `static=True`
  * Changed `Method.is_candidate()` to accept `staticmethod`
    and `classmethod` instances
  * Changed `Method.wrap_candidate()` to accept `staticmethod`
    and `classmethod` instances
  * Changed `ImplementationError` which now resembles errors from multiple
    interfaces as well as functions marked with `@override` which do not
    actually override a member
  * Removed `StaticAttribute`
  * Fixed spelling mistake in `ValueError` raised by `Property.satisfy()`
* Added `nr.types.structured`
  * Successor to `nr.config`, which is now deprecated

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
