
# v0.0.6 (2020-04-13)

* Add `ObjectMapper.cast()`

# v0.0.5 (2020-04-13)

* Add `OptionalType`
* Update `AnyType.from_typedef()` to support `typing.Any`
* Update dependency on `nr.collections` from `~0.0.1` to `^0.1.0`

# v0.0.4 (2020-04-10)

* Add `StandardTypeResolver.register_union_member()`
* Update error message in `ObjectType.instance_check()`

# v0.0.3 (2020-03-24)

* Rename nr.databind.core.struct.struct() to .make_struct(), import into nr.databind.core and add unit test

# v0.0.2 (2020-03-24)

* `_StructMeta.__getattr__()` now returns the wrapped Struct type if a field is of type StructType

# v0.0.1 (2020-03-20)

* Initial release.
