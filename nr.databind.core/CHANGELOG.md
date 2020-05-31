# Changelog

## v0.0.15 (2020-05-16)

* Change `FieldSpec.from_dict()`: Now accepts non-Field objects in dictionary values, expecting
  that the value represents a Field type definition and creates a new Field from it. This effects
  `make_struct()`, allowing the creation of structs with a leaner syntax.

## v0.0.14 (2020-05-15)

* Add `FieldSpec.__setitem__()`

## v0.0.13 (2020-05-14)

* Raise `TypeError` if unexpected keyword argument is passed to `Struct` constructor

## v0.0.12 (2020-05-13)

* Added `FieldSpec.__delitem__()`, `FieldSpec.__copy__()` and `FieldSpec.copy()`

## v0.0.11 (2020-05-13)

* `Strict` decoration is now inherited by subclasses
* Add `cast_struct()` function
* Fix `Node.get_decoration()` for ClassDecorations

## v0.0.10 (2020-05-11)

* Add `Validator.test()` method
* Add `Validator.choices()` static method

## v0.0.9 (2020-04-18)

* Fix `Struct.__ne__()`

## v0.0.8 (2020-04-16)

* Add `IDataType.get_decorations()`

## v0.0.7 (2020-04-14)

* `MultiType` now matches on `typing.Union`

## v0.0.6 (2020-04-13)

* Add `ObjectMapper.cast()`

## v0.0.5 (2020-04-13)

* Add `OptionalType`
* Update `AnyType.from_typedef()` to support `typing.Any`
* Update dependency on `nr.collections` from `~0.0.1` to `^0.1.0`

## v0.0.4 (2020-04-10)

* Add `StandardTypeResolver.register_union_member()`
* Update error message in `ObjectType.instance_check()`

## v0.0.3 (2020-03-24)

* Rename nr.databind.core.struct.struct() to .make_struct(), import into nr.databind.core and add unit test

## v0.0.2 (2020-03-24)

* `_StructMeta.__getattr__()` now returns the wrapped Struct type if a field is of type StructType

## v0.0.1 (2020-03-20)

* Initial release.
