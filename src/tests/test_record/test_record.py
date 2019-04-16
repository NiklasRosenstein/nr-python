
import copy
import os
import pytest
import sys

from nr.types import record

sys.path.append(os.path.dirname(__file__))


def _test_record(m):
  s = m.Student('Peter', mail='peter@mit.com', school='MIT')
  assert s.as_dict() == {'name': 'Peter', 'mail': 'peter@mit.com', 'age': 50, 'school': 'MIT'}

  c = m.Change('NEW', 'user', 'name', 'John Smith')
  assert c.type == 'NEW'
  assert c.section == 'user'
  assert c.key == 'name'
  assert c.value == 'John Smith'

  assert c == c
  assert copy.copy(c) == c

  assert list(m.Person.__fields__) == ['name', 'mail', 'age']
  assert list(m.Student.__fields__) == ['name', 'mail', 'age', 'school']
  assert list(m.Change.__fields__) == ['type', 'section', 'key', 'value']

  assert repr(c) == "Change(type='NEW', section='user', key='name', value='John Smith')"
  assert repr(c) == str(c)


@pytest.mark.skipif(sys.version_info < (3,6),
                    reason="requires python3.6 or higher")
def test_record_36():
  import _record36
  _test_record(_record36)


def test_record():
  import _record
  _test_record(_record)


def test_module_inheritablity():
  class Person(record):
    name = record.Field(str)
    mail = record.Field(str)
  assert issubclass(Person, record.Record)
  assert Person.__bases__ == (record.Record,)
  assert Person('John', 'foo@bar.com').name == 'John'
  assert Person('John', 'foo@bar.com').mail == 'foo@bar.com'
