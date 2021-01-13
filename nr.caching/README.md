# nr.caching

A simple key-value caching API with default implementations for an SQLite3 storage backend and
a JSON convenience layer.

## Quickstart

```py
from nr.caching.sqlite import SqliteStore
from nr.caching.json import JsonCache

cache = JsonCache(SqliteStore('.cache.db'))
data = cache.loading('my-namespace', parameters, lambda: expensive_function(*parameters))
```

---

<p align="center">Copyright &copy; 2021 Niklas Rosenstein</p>
