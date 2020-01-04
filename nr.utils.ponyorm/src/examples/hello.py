
from nr.utils.ponyorm.appdb import AppDatabase, Optional, Required
from nr.utils.ponyorm.converters import EnumConverter
from nr.utils.ponyorm import get_or_create
from pony.orm import Database, db_session
import enum

appdb = AppDatabase(__name__)
appdb.register_converter(EnumConverter)

class PersonType(enum.Enum):
  Student = 'Student'

class Person(appdb.Entity):
  name = Required(str)
  type = Required(PersonType)


def main():
  db = Database(provider='sqlite', filename=':memory:')
  appdb.bind_to(db)
  db.generate_mapping(create_tables=True)

  with db_session():
    john, created = get_or_create(
      Person,
      {'name': 'John Swag'},
      {'type': PersonType.Student})
    print('Hello, {} ({}, created: {})'.format(john.name, john.type, created))


if __name__ == '__main__':
  main()
