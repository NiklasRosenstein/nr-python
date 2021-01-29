
> Note: This package is in the dangerous land of `0.x.y` versions and may be subject to breaking
> changes with minor version increments.

# nr.caching

A simple key-value caching API with default implementations for an SQLite3 storage backend and
a JSON convenience layer.

## Quickstart

```py
from nr.caching.sqlite import SqliteStore
from nr.caching.json import hash_args, JsonCacheFactory

caching_backend = SqliteStore('.cache.db')
cache_factory = JsonCacheFactory(caching_backend, default_exp=60)
data = cache_factory.namespace('my-namespace').loading(
  f'expensive_function_{hash_args(parameters)}',
  lambda: expensive_function(*parameters))
```

---

<p align="center">Copyright &copy; 2021 Niklas Rosenstein</p>
