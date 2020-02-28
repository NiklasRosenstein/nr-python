
from nr.databind.core import *
from nr.databind.core.decoration import LocationMetadataDecoration
from nr.databind.json import JsonFieldName, JsonStrict, JsonDeserializer
from nr.pylang.utils import NotSet
from typing import Optional, List, Dict
from ..fixtures import mapper
import pytest
import six
import sys
import textwrap


def test_field_creation():
  a = Field(Optional[List[str]])
  b = Field(List[str], nullable=True)
  assert a == b


def test_struct(mapper):

  def _test_object_def(Person):
    assert hasattr(Person, '__fields__')
    assert list(Person.__fields__.keys()) == ['name', 'age', 'telephone_numbers']
    fields = Person.__fields__

    assert isinstance(fields['name'].datatype, StringType)
    assert isinstance(fields['age'].datatype, IntegerType)
    assert isinstance(fields['telephone_numbers'].datatype, CollectionType)
    assert isinstance(fields['telephone_numbers'].datatype.item_type, StringType)

    assert not fields['name'].nullable
    assert fields['age'].nullable
    assert not fields['telephone_numbers'].nullable

  from typing import List, Optional

  class Person(Struct):
    JsonStrict()
    name = Field(str)
    age = Field(int, default=None)
    telephone_numbers = Field(List[str], JsonFieldName('telephone-numbers'), default=list)

  _test_object_def(Person)

  if sys.version >= '3.6':
    # TODO(nrosenstein): Just using globals()/locals() in the exec_() call
    #   does not work as expected, it cannot find the local variables then.
    scope = globals().copy()
    scope.update(locals())
    six.exec_(textwrap.dedent('''
      class Person(Struct):
        JsonStrict()
        name: str
        age: int = None
        telephone_numbers: List[str] = list

      Person.__fields__['telephone_numbers'].decorations.append(JsonFieldName('telephone-numbers'))
      _test_object_def(Person)
      '''), scope)

  payload = {'name': 'John Wick', 'telephone-numbers': ['+1 1337 38991']}
  expected = Person('John Wick', age=None, telephone_numbers=['+1 1337 38991'])
  assert mapper.deserialize(payload, Person) == expected

  payload = {'name': 'John Wick', 'age': 52}
  expected = Person('John Wick', age=52, telephone_numbers=[])
  assert mapper.deserialize(payload, Person) == expected

  payload = {'name': 'John Wick', 'age': None}
  expected = Person('John Wick', age=None, telephone_numbers=[])
  assert mapper.deserialize(payload, Person) == expected

  payload = {'name': 'John Wick', 'telephone_numbers': ['+1 1337 38991']}
  with pytest.raises(SerializationValueError) as excinfo:
    mapper.deserialize(payload, Person)
  if six.PY2:
    assert excinfo.value.message == "strict object type \"Person\" does not allow additional keys on extract, but found set(['telephone_numbers'])"
  else:
    assert excinfo.value.message == "strict object type \"Person\" does not allow additional keys on extract, but found {'telephone_numbers'}"

  payload = [
    {'name': 'John Wick', 'age': 54},
    {'name': 'Barbara Streisand', 'telephone-numbers': ['+1 BARBARA STREISAND']},
  ]
  expected = [
    Person('John Wick', age=54, telephone_numbers=[]),
    Person('Barbara Streisand', telephone_numbers=['+1 BARBARA STREISAND']),
  ]
  deserialized = mapper.deserialize(payload, [Person])
  assert deserialized == expected
  assert mapper.serialize(deserialized, [Person]) == payload


def test_struct_args_vs_kwargs():
  class MyStruct(Struct):
    a = Field(str)
    b = Field(int)

  MyStruct('foo', 42)
  with pytest.raises(TypeError):
    MyStruct('foo', 'bar')

  MyStruct('foo', b=42)
  with pytest.raises(TypeError):
    MyStruct('foo', b='bar')


def test_struct_equality(mapper):
  class Obj(Struct):
    a = Field(int)

  assert Obj(1) == Obj(1)
  assert not (Obj(1) == Obj(2))
  assert Obj(1) != Obj(2)
  assert not (Obj(1) != Obj(1))


def test_struct_subclassing(mapper):

  class Person(Struct):
    name = Field(str)

  class Student(Person):
    student_id = Field(str)

  assert len(Student.__fields__) == 2
  assert list(Student.__fields__) == ['name', 'student_id']
  assert Student.__fields__['name'] is Person.__fields__['name']
  assert Student('John Wick', '4341115409').name == 'John Wick'
  assert Student('John Wick', '4341115409').student_id == '4341115409'


def test_struct_def(mapper):
  class A(Struct):
    __fields__ = ['a', 'c', 'b']
  assert isinstance(A.__fields__, FieldSpec)
  assert list(A.__fields__.keys()) == ['a', 'c', 'b']
  assert A.__fields__['a'].datatype == AnyType()
  assert A.__fields__['c'].datatype == AnyType()
  assert A.__fields__['b'].datatype == AnyType()
  assert isinstance(A.a, Field)

  class B(Struct):
    __fields__ = [
      ('a', int),
      ('b', str, 'value')
    ]
  assert isinstance(B.__fields__, FieldSpec)
  assert list(B.__fields__.keys()) == ['a', 'b']
  assert B.__fields__['a'].datatype == IntegerType()
  assert B.__fields__['b'].datatype == StringType()

  class C(Struct):
    __annotations__ = [
      ('a', int),
      ('b', str, 'value')
    ]
  assert isinstance(C.__fields__, FieldSpec)
  assert list(C.__fields__.keys()) == ['a', 'b']
  assert C.__fields__['a'].datatype == IntegerType()
  assert C.__fields__['b'].datatype == StringType()


def test_fieldspec_equality(mapper):
  assert FieldSpec() == FieldSpec()
  assert FieldSpec([Field(object, name='a')]) == FieldSpec([Field(object, name='a')])
  assert FieldSpec([Field(object, name='a')]) != FieldSpec([Field(object, name='b')])


def test_fieldspec_update(mapper):

  class TestObject(Struct):
    test = Field(int)
    foo = Field(str)

  assert list(TestObject.__fields__.keys()) == ['test', 'foo']
  assert TestObject.test is TestObject.__fields__['test']
  assert TestObject.foo is TestObject.__fields__['foo']
  assert TestObject.__fields__['foo'].name == 'foo'

  fields = [Field(str, name='test'), Field(object, name='bar')]
  TestObject.__fields__.update(fields)

  assert list(TestObject.__fields__.keys()) == ['test', 'foo', 'bar']
  assert TestObject.test is TestObject.__fields__['test']
  assert TestObject.foo is TestObject.__fields__['foo']
  assert TestObject.bar is TestObject.__fields__['bar']
  assert TestObject.__fields__['bar'].name == 'bar'


def test_custom_collection(mapper):

  class Items(Collection, list):
    item_type = str
    def join(mapper):
      return ','.join(mapper)

  from nr.databind.core.collection import _CollectionMeta
  assert type(Items) == _CollectionMeta
  assert Items.datatype == CollectionType(StringType(), Items)

  class Data(Struct):
    items = Field(Items)

  payload = {'items': ['a', 'b', 'c']}
  data = mapper.deserialize(payload, Data)
  assert data == Data(['a', 'b', 'c'])
  assert data.items.join() == 'a,b,c'

  assert Data(['a', 'b', 'c']).items.join() == 'a,b,c'


def test_inline_schema_definition(mapper):
  datatype = translate_type_def({
    'a': Field(int),
    'b': Field(str),
  })
  assert type(datatype) == StructType
  assert sorted(datatype.struct_cls.__fields__.keys()) == ['a', 'b']

  class Test(Struct):
    field1 = Field(int)
    field2 = Field({
      'a': Field(int),
      'b': Field(str),
    })
  assert isinstance(Test.field1, Field)
  assert isinstance(Test.field2, Field)
  assert Test.field2.datatype.struct_cls.__name__ == 'field2'
  assert Test.field2.datatype.struct_cls.__qualname__ == 'Test.field2'


def test_struct_class_overridable_attribute():

  class MyBaseClass(Struct):
    __annotations__ = [
      ('a', str),
      ('b', int),
      ('c', float)
    ]

  assert sorted(MyBaseClass.__fields__) == ['a', 'b', 'c']

  class MySubClass(MyBaseClass):
    b = 42

  assert MySubClass.b == MySubClass.__fields__['b']
  assert MySubClass.b.default == 42
  assert MyBaseClass.b.default == NotSet
  assert MySubClass.b.parent == MyBaseClass.b

  assert MySubClass('value of a', c=1.0) == MySubClass('value of a', 42, 1.0)

  class OtherSubclass(MyBaseClass):
    b = Field(str)

  assert OtherSubclass.__fields__['b'].datatype == StringType()


def test_json_custom_deserializer(mapper):

  import re

  class Author(Struct):
    name = Field(str)
    email = Field(str)

    AUTHOR_EMAIL_REGEX = re.compile(r'([^<]+)<([^>]+)>')

    def __str__(self):
      return '{} <{}>'.format(self.name, self.email)

    @JsonDeserializer
    def __deserialize(context, location):
      if isinstance(location.value, str):
        match = Author.AUTHOR_EMAIL_REGEX.match(location.value)
        if match:
          author = match.group(1).strip()
          email = match.group(2).strip()
          return Author(author, email)
      raise NotImplementedError

  author = mapper.deserialize('Me <me@example.org>', Author)
  assert author == Author('Me', 'me@example.org')

  author = mapper.deserialize('Me <me@example.org>', Author,
    decorations=[LocationMetadataDecoration()])
  assert author.__databind__ is not None
  assert author.__databind__['location'].value == 'Me <me@example.org>'
