# Changelog

### v3.1.0 (2019-09-27)

* Add `nr.types.persist` module
  * Requires `nr.fs >= 1.5.0`, which can be installed with the `[persist]` extra

### v3.0.3 (2019-09-18)

* `nr.types.structured`
  * `FieldSpec.from_list_def()` now supports `str` and `Field` items
  * `FieldSpec.from_list_def()` is now used if `__field__` is used when the
    `Object` subclass is constructed

### v3.0.2 (2019-09-18)

* `nr.types.structured`
  * Add `PythonType` and a translator for it
  * Add proxy translator for handling strings (turned into a `ForwardDecl`),
    but the resolving part still needs to be implemented

### v3.0.1 (2019-09-18)

* `nr.types.structured`
  * Fix bug in `WildcardField()` constructor that passes an incorrect type
    to the `DictType()` constructor

### v3.0.0 (2019-09-18)

* Big reshaping of the library.

### v2.5.5 (2019-08-22)

* `nr.types.interface`
  * (#7) Updated `ImplementationError.__str__()` to render `{}` inset of `set()`
    when the implementation does not meet the requierments of "no interfaces"
    (ie. when specifying `@override` for an implementation of no interfaces).
  * (#8) Implemented interfaces are now inherited by implementation subclasses.
* `nr.types.structured`
  * (#6) Add `FieldSpec.update()` function in order to allow updating the
    fields of an `Object` class (useful for decorators)
  * `Object` metaclass now overrides `__dir__()` and `__getattr__()` to return
    items from its `__fields__` attribute, allowing updates to the `FieldSpec`
    to automatically propagate as class members.
  * (#5) Add `MetadataField` class
  * Add `nr.types.structured.utils` module with `add_origin_metadata_field()` decorator
  * Add `nr.types.structured.utils.yaml` module which allows to load Yaml data
    while keepin track of filename and line number.
* `nr.types.stream`
  * Methods on the `stream` class wrapped by the `@_dualmethod` decorator are
    now proper function objects, inheriting the wrapped functions' docstrings
    (useful for `$ pydoc nr.types.stream`).


### v2.5.4 (2019-08-15)

* Subclasses of other `structured.Object` subclasses now properly inherit
  the parent object's fields

### v2.5.3 (2019-08-08)

* Hotfix for Python 2 and `sumtype.constructor(mixins)` keyword argument

### v2.5.2 (2019-08-08)

* `sumtype.constructor()` now accepts multiple field names as arguments
* `sumtype` now supports a `__default__` constructor (can be set to a string
  or a `Constructor` instance)

### v2.5.1 (2019-08-08)

* Fixed unpacking `MethodType` in `Implementation.__metanew__()`
  * This error would surface when using a `@classmethod` in an interface
  * Added a testcase for this part of the metaclass that checks if the
    implementation satisfies the interfaces
* Fix `RuntimeError` raised when using `attr(default=None)`
* Allow using `@staticattr` to decorate methods, which will then be kept
  as an actual member on the interface. A common use case will be to define
  a `@classmethod` on the interface itself.
* Add `record` and `field` member to the `nr.types.sumtype` class, which act
  as aliases for `nr.types.record.Record` and `nr.types.record.Field`.
* `nr.sumtype.member_of()` now accepts `CleanRecord` subclasses additionally
  to `Constructor` instances.

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
