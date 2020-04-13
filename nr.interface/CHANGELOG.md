
# 0.0.2 (2020-04-13)

* Added `Method.original` attribute, which points to the original function
  defined in the interface
* Added `@optional` decorator for Interface methods
* Added a unit test for implementing an interface in a metaclass
* Fix some type annotations
* Override `__name__` and `__qualname__` of the `lambda_type` that is
  created in `Interface.__new__()`
* Update dependency on `nr.collections` from `~0.0.1` to `^0.1.0`
