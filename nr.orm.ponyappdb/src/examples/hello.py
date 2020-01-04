
from nr.orm.ponyappdb import AppDatabase, Optional, Required
from pony.orm import Database, db_session


appdb = AppDatabase(__name__)

class Person(appdb.Entity):
  name = Required(str)


def main():
  db = Database(provider='sqlite', filename=':memory:')
  appdb.bind_to(db)
  db.generate_mapping(create_tables=True)

  with db_session():
    Person(name='John Swag')

  with db_session():
    print('Hello,', Person.select().first().name)


if __name__ == '__main__':
  main()
