# -*- coding: utf8 -*-
# Copyright (c) 2019 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

import pytest
import six
import sys
import textwrap
from nr.types import NotSet
from nr.types.structured import *


def test_locator_str_empty():
  assert str(Locator.Proxy([])) == '$'


def test_locator_str_simple():
  assert str(Locator.Proxy(['foobar'])) == '$.foobar'
  assert str(Locator.Proxy(['spam', 'baz'])) == '$.spam.baz'
  assert str(Locator.Proxy([0, 1, 5])) == '$[0][1][5]'


def test_locator_str_mixed():
  assert str(Locator.Proxy(['foobar', 3, 'type'])) == '$.foobar[3].type'


def test_locator_str_escape():
  assert str(Locator.Proxy(['root', 1, 'needs:escaping'])) == '$.root[1]."needs:escaping"'
  assert str(Locator.Proxy(['"also needs escaping'])) == '$."\\"also needs escaping"'
  assert str(Locator.Proxy(['no-escaping'])) == '$.no-escaping'


def test_locator_resolve():
  data = {'2.4.0': {'foo': {'bar': {'spam-egg': []}}}}

  locator = Locator.Proxy(['2.4.0', 'foo', 'bar', 'spam-egg'])
  assert locator.resolve(data) == []

  locator = Locator.Proxy(['2.4.0', 'foo', 'bar', 'spam-eggzzz'])
  with pytest.raises(KeyError) as excinfo:
    locator.resolve(data)
  assert str(excinfo.value) == repr(str(locator))

  locator = Locator.Proxy(['2.4.0', 'foo', 'bar', 'spam-egg', 1])
  with pytest.raises(IndexError) as excinfo:
    locator.resolve(data)
  assert str(excinfo.value) == 'list index out of range at $."2.4.0".foo.bar.spam-egg[1]'


def test_locator_resolve_and_emplace():
  proxy = Locator.Proxy(['foo', 1, 'bar'])
  assert str(proxy) == '$.foo[1].bar'

  data = {'foo': [{'bar': 11}]}
  with pytest.raises(IndexError) as exc:
    proxy.resolve(data)

  data = {'foo': [{'bar': 11}, {'bar': 42}]}
  assert proxy.resolve(data) == 42

  proxy = proxy.emplace(proxy.resolve(data), IntegerType())
  assert proxy.extract() == 42


def test_string_type():
  locator = Locator.Proxy(['a', 'b', 'c'], "foobar", StringType())
  assert locator.extract() == "foobar"

  locator = Locator.Proxy(['a', 'b', 'c'], 42, StringType())
  with pytest.raises(ExtractTypeError) as excinfo:
    locator.extract()
  assert str(excinfo.value.locator) == '$.a.b.c'

  locator = Locator.Proxy(['a', 'b', 'c'], 42, StringType(strict=False))
  assert locator.extract() == "42"


def test_array_type():
  locator = Locator.Proxy(['a', 'b'], ["foo", "bar", "baz"], ArrayType(StringType()))
  assert locator.extract() == ["foo", "bar", "baz"]

  locator = Locator.Proxy(['a', 'b'], ["foo", 42, "baz"], ArrayType(StringType()))
  with pytest.raises(ExtractTypeError) as excinfo:
    locator.extract()
  assert str(excinfo.value.locator) == '$.a.b[1]'

  locator = Locator.Proxy(['a', 'b'], ["foo", 42, "baz"], ArrayType(StringType(strict=False)))
  assert locator.extract() == ["foo", "42", "baz"]


def test_dict_type():
  locator = Locator.Proxy(['foo'], "Hello World!", DictType(StringType()))
  with pytest.raises(ExtractTypeError) as excinfo:
    locator.extract()
  assert str(excinfo.value.locator) == '$.foo'

  locator = Locator.Proxy(['foo'], {"msg": "Hello World!"}, DictType(StringType()))
  assert locator.extract() == {"msg": "Hello World!"}

  typedef = ArrayType(DictType(StringType()))
  locator = Locator.Proxy(['root'], [{"a": "b"}, {"c": "d", "e": "f"}], typedef)
  assert locator.extract() == [{"a": "b"}, {"c": "d", "e": "f"}]

  typedef = ArrayType(DictType(StringType()))
  locator = Locator.Proxy(['root'], [{"a": "b"}, {"c": 0.2, "e": "f"}], typedef)
  with pytest.raises(ExtractTypeError) as excinfo:
    locator.extract()
  assert str(excinfo.value.locator) == '$.root[1].c'


def test_union_type():
  datatype = UnionType({'int': IntegerType(), 'string': StringType()})
  assert extract({'type': 'int', 'int': 42}, datatype) == {'type': 'int', 'int': 42}
  assert extract({'type': 'string', 'string': 'foo'}, datatype) == {'type': 'string', 'string': 'foo'}
  with pytest.raises(ExtractValueError):
    extract({'type': 'int', 'string': 'foo'}, datatype) == {'type': 'int', 'string': 'foo'}


def test_translate_field_type():
  assert isinstance(translate_field_type(str), StringType)
  assert isinstance(translate_field_type([str]), ArrayType)
  assert isinstance(translate_field_type([str]).item_type, StringType)
  assert isinstance(translate_field_type([]), ArrayType)
  assert isinstance(translate_field_type([]).item_type, AnyType)
  assert isinstance(translate_field_type({str}), DictType)
  assert isinstance(translate_field_type({str}).value_type, StringType)
  assert isinstance(translate_field_type({"key": str}), DictType)
  assert isinstance(translate_field_type({"key": str}).value_type, StringType)

  with pytest.raises(InvalidTypeDefinitionError):
    translate_field_type([str, str])

  assert isinstance(translate_field_type(StringType), StringType)

  with pytest.raises(TypeError):
    translate_field_type(ArrayType)  # not enough arguments

  typedef = ArrayType(StringType())
  assert translate_field_type(typedef) is typedef


def test_translate_field_type_typing():
  from typing import List, Dict
  assert isinstance(translate_field_type(List[str]), ArrayType)
  assert isinstance(translate_field_type(List[str]).item_type, StringType)
  assert isinstance(translate_field_type(List), ArrayType)
  assert isinstance(translate_field_type(List).item_type, AnyType)
  assert isinstance(translate_field_type(Dict[str, str]), DictType)
  assert isinstance(translate_field_type(Dict[str, str]).value_type, StringType)
  assert isinstance(translate_field_type(Dict), DictType)
  assert isinstance(translate_field_type(Dict).value_type, AnyType)
  with pytest.raises(InvalidTypeDefinitionError):
    translate_field_type(Dict[int, str])


def test_object():

  def _test_object_def(Person):
    assert hasattr(Person, '__fields__')
    assert list(Person.__fields__.keys()) == ['name', 'age', 'telephone_numbers']

    assert isinstance(Person.name.datatype, StringType)
    assert isinstance(Person.age.datatype, IntegerType)
    assert isinstance(Person.telephone_numbers.datatype, ArrayType)
    assert isinstance(Person.telephone_numbers.datatype.item_type, StringType)

    assert not Person.name.nullable
    assert Person.age.nullable
    assert Person.telephone_numbers.nullable

  from typing import List, Optional

  class Person(Object):
    name = Field(str)
    age = Field(int, default=None)
    telephone_numbers = Field(List[str], nullable=True, default=lambda: [])

    class Meta:
      extract_mapping = {'telephone_numbers': 'telephone-numbers'}
      strict = True

  _test_object_def(Person)

  if sys.version >= '3.6':
    # TODO(nrosenstein): Just using globals()/locals() in the exec_() call
    #   does not work as expected, it cannot find the local variables then.
    scope = globals().copy()
    scope.update(locals())
    six.exec_(textwrap.dedent('''
      class Person(Object):
        name: str
        age: int = None
        telephone_numbers: Optional[List[str]] = lambda: []
      _test_object_def(Person)
      '''), scope)

  payload = {'name': 'John Wick', 'telephone-numbers': ['+1 1337 38991']}
  expected = Person('John Wick', age=None, telephone_numbers=['+1 1337 38991'])
  assert extract(payload, Person) == expected

  payload = {'name': 'John Wick', 'age': 52}
  expected = Person('John Wick', age=52, telephone_numbers=[])
  assert extract(payload, Person) == expected

  payload = {'name': 'John Wick', 'age': None}
  expected = Person('John Wick', age=None, telephone_numbers=[])
  assert extract(payload, Person) == expected

  payload = {'name': 'John Wick', 'telephone_numbers': ['+1 1337 38991']}
  with pytest.raises(ExtractValueError) as excinfo:
    extract(payload, Person)
  if six.PY2:
    assert excinfo.value.message == "strict object type \"Person\" does not allow additional keys on extract, but found set(['telephone_numbers'])"
  else:
    assert excinfo.value.message == "strict object type \"Person\" does not allow additional keys on extract, but found {'telephone_numbers'}"

  payload = [
    {'name': 'John Wick', 'age': 54},
    {'name': 'Barbara Streisand', 'age': None, 'telephone-numbers': ['+1 BARBARA STREISAND']},
  ]
  expected = [
    Person('John Wick', age=54, telephone_numbers=[]),
    Person('Barbara Streisand', age=None, telephone_numbers=['+1 BARBARA STREISAND']),
  ]
  assert extract(payload, List[Person]) == expected


def test_object_subclassing():

  class Person(Object):
    name = Field(str)

  class Student(Person):
    student_id = Field(str)

  assert len(Student.__fields__) == 2
  assert list(Student.__fields__) == ['name', 'student_id']
  assert Student.name is Person.name
  assert Student('John Wick', '4341115409').name == 'John Wick'
  assert Student('John Wick', '4341115409').student_id == '4341115409'


def test_fieldspec_update():

  class TestObject(Object):
    test = Field(int)
    foo = Field(str)

  assert list(TestObject.__fields__.keys()) == ['test', 'foo']
  assert hasattr(TestObject, 'test')
  assert hasattr(TestObject, 'foo')
  assert set(dir(TestObject)).issuperset(set(['test', 'foo']))

  fields = [('test', Field(str)), ('bar', Field(object))]
  TestObject.__fields__.update(fields)

  assert list(TestObject.__fields__.keys()) == ['test', 'foo', 'bar']
  assert hasattr(TestObject, 'test')
  assert hasattr(TestObject, 'foo')
  assert hasattr(TestObject, 'bar')
  assert set(dir(TestObject)).issuperset(set(['test', 'foo', 'bar']))


def test_metadata_field():

  class Test(Object):
    meta = MetadataField(str)
    value = Field(int)

    class Meta:
      strict = True

  assert Test('foo', 42).meta == 'foo'
  assert Test('foo', 42).value == 42

  data = {'meta': 'foo', 'value': 42}
  with pytest.raises(ExtractValueError) as excinfo:
    extract(data, Test)
  assert 'does not allow additional keys on extract' in str(excinfo.value)

  data = {'value': 42}
  assert extract(data, Test).meta is None
  assert extract(data, Test).value == 42

  class Map(dict):
    pass
  data = Map({'value': 42})
  data.__metadata__ = {'meta': 'foo'}
  assert extract(data, Test).meta == 'foo'
  assert extract(data, Test).value == 42

  # Test read function that doesn't add to handled_keys.

  def read(locator, handled_keys):
    return locator.value().get('_metadata', {}).get('meta', NotSet)

  Test.meta.read = read
  data = {'_metadata': {'meta': 'bar'}, 'value': 42}
  with pytest.raises(ExtractValueError) as excinfo:
    extract(data, Test)
  assert 'does not allow additional keys on extract' in str(excinfo.value)

  Test.Meta.strict = False
  assert extract(data, Test).meta == 'bar'
  assert extract(data, Test).value == 42

  # Test read function that _does_ add to handled_keys.

  def read(locator, handled_keys):
    handled_keys.add('_metadata')  # allow even in _strict mode
    return locator.value().get('_metadata', {}).get('meta', NotSet)

  Test.meta.read = read
  Test.Meta.strict = True
  data = {'_metadata': {'meta': 'bar'}, 'value': 42}
  assert extract(data, Test).meta == 'bar'
  assert extract(data, Test).value == 42


def _test_forward_decl_node(Node):
  payload = {
    'id': 'root',
    'children': [
      {'id': 'a'},
      {'id': 'b', 'children': [{'id': 'c'}]}
    ]
  }
  expect = Node('root', [
    Node('a'),
    Node('b', [Node('c')])
  ])
  got = extract(payload, Node)
  assert got == expect

  expect = {
    'id': 'root',
    'children': [
      {'id': 'a', 'children': []},
      {'id': 'b', 'children': [{'id': 'c', 'children': []}]}
    ]
  }
  assert store(got) == expect


def test_forward_decl():
  Node = ForwardDecl('Node')
  class Node(Object):
    id = Field(str)
    children = Field([Node], default=list)
  _test_forward_decl_node(Node)


class _GlobalNode(Object):
  id = Field(str)
  children = Field([ForwardDecl('_GlobalNode')], default=list)


def test_forward_decl_global():
  _test_forward_decl_node(_GlobalNode)


@pytest.mark.skip("Currently not supported.")
def test_forward_decl_inline():
  class Node(Object):
    id = Field(str)
    children = Field([ForwardDecl('Node')], default=list)
  _test_forward_decl_node(Node)


def test_extract_custom_locator():
  data = {'a': {'b': 42}}
  locator = Locator.Proxy(['a', 'b'])
  assert extract(locator.resolve(data), IntegerType(), locator) == 42
  with pytest.raises(ExtractTypeError):
    extract(locator.resolve(data), StringType(), locator)
  assert extract(locator.resolve(data), StringType(strict=False), locator) == '42'
