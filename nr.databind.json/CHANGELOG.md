# Changelog

### v0.0.9 (2020-05-16)

* `MultiTypeSerializer` now catches `SerializationError` instead of 
  `SerializationTypeError` when testing the deserialization of a `MultiType`
  member

### v0.0.8 (2020-05-11)

* `Validator` decoration is now treated correctly and `TypeError`/`ValueError`
  from it is converted appropriately

### v0.0.7 (2020-04-16)

* `PythonClassConverter` and `StructConverter` now respect the decorations
  returned by `Node.get_decoration()`

### v0.0.6 (2020-04-13)

* Set the "mapper" key in the `Struct.__databind__` and
  `Collection.__databind__` metadata dictionary on de-serialization.

### v0.0.5 (2020-04-13)

* Add `OptionalSerializer`
* Add `JsonEncoder.with_mapper()` factory function
* Update dependency on `nr.collections` from `~0.0.1` to `^0.1.0`
* Fix `JsonSerializer` decoration constructor

### v0.0.4 (2020-03-24)

* Fix parsing of `date` types

### v0.0.3 (2020-03-24)

* Fix default format for `date` and `datetime` (de-) serializer

### v0.0.2 (2020-03-21)

* Respect `SerializeAs` decoration when (de-) serializing `PythonClassType`

### v0.0.1 (2020-03-20)

* Initial version.
