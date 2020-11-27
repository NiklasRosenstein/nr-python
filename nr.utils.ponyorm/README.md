
> Note: This package is in the dangerous land of `0.x.y` versions and may be subject to breaking
> changes with minor version increments.

# nr.utils.ponyorm

Utilities for [Pony ORM](https://ponyorm.org/).

### Composable databases

Applications with plugin interfaces may choose to allow the use of a common
database, accessed via the same Pony ORM database object. The
`nr.utils.ponyorm.appdb` provides classes to allow just that.

Example:

```python
from nr.utils.ponyorm.appdb import AppDatabase, Optional, Required
appdb = AppDatabase(__name__)
class Person(appdb.Entity):
  name = Required(str)
  # etc. etc.
```

Then from the application startup logic:

```python
from pony.orm import Database
db = Database()
for appdb in load_all_application_databases():  # ominous functions
  appdb.bind_to(db)
db.generate_mapping(create_tables=True)
```

### Common converters

Provides common converter implementations that are not built into Pony ORM.
All converters can be registered via `AppDatabase.register_converter(converter_cls)`
or with `nr.utils.ponyorm.converters.register_converter(db, converter_cls)`.

Available converters are

* `EnumConverter`

### Utility functions

* `get_db(entity)`
* `get_one(entity_cls, kwargs)`
* `get_or_create(entity_cls, get, set=None)`
* `upsert(entity_cls, get, set=None, mutate=True)`

---

<p align="center">Copyright &copy; 2020 Niklas Rosenstein</p>
