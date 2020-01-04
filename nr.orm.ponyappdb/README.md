# nr.orm.ponyappdb

Composable entities based on Pony ORM. Allows you to create an "app database"
that can be dynamically bound to an actual Pony ORM database object on
application startup.

Example:

```python
from nr.orm.ponyappdb import AppDatabase, Optional, Required
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
