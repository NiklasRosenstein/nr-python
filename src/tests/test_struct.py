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

import decimal
import pytest
import six
import sys
import textwrap
from nr.types.singletons import NotSet
from nr.types.struct import *


def make_location(path, value=None, datatype=None):
  return Path(path).to_location(value, datatype)


class TestCore(object):

  def setup_method(self, method):
    self.json_mapper = JsonObjectMapper()
    self.type_mapper = DefaultTypeMapper()

  def test_location_str_empty(self):
    assert str(make_location([]).path) == '$'

  def test_location_str_simple(self):
    assert str(make_location(['foobar']).path) == '$.foobar'
    assert str(make_location(['spam', 'baz']).path) == '$.spam.baz'
    assert str(make_location([0, 1, 5]).path) == '$[0][1][5]'

  def test_location_str_mixed(self):
    assert str(make_location(['foobar', 3, 'type']).path) == '$.foobar[3].type'

  def test_location_str_escape(self):
    assert str(make_location(['root', 1, 'needs:escaping']).path) == '$.root[1]."needs:escaping"'
    assert str(make_location(['"also needs escaping']).path) == '$."\\"also needs escaping"'
    assert str(make_location(['no-escaping']).path) == '$.no-escaping'

  def test_location_resolve(self):
    data = {'2.4.0': {'foo': {'bar': {'spam-egg': []}}}}

    location = make_location(['2.4.0', 'foo', 'bar', 'spam-egg'])
    assert location.path.resolve(data) == []

    location = make_location(['2.4.0', 'foo', 'bar', 'spam-eggzzz'])
    with pytest.raises(KeyError) as excinfo:
      location.path.resolve(data)
    assert str(excinfo.value) == repr(str(location.path))

    location = make_location(['2.4.0', 'foo', 'bar', 'spam-egg', 1])
    with pytest.raises(IndexError) as excinfo:
      location.path.resolve(data)
    assert str(excinfo.value) == 'list index out of range at $."2.4.0".foo.bar.spam-egg[1]'

  def test_location_resolve_and_emplace(self):
    proxy = make_location(['foo', 1, 'bar'])
    assert str(proxy.path) == '$.foo[1].bar'

    data = {'foo': [{'bar': 11}]}
    with pytest.raises(IndexError) as exc:
      proxy.path.resolve(data)

    data = {'foo': [{'bar': 11}, {'bar': 42}]}
    assert proxy.path.resolve(data) == 42

    proxy = proxy.path.to_location(proxy.path.resolve(data), IntegerType())
    assert self.json_mapper.deserialize(proxy) == 42

  def test_decimal_type(self):
    location = make_location(['value'], '42.0', DecimalType(float, strict=False))
    assert self.json_mapper.deserialize(location) == pytest.approx(42.0)

    location = make_location(['value'], '42.0', DecimalType(float, strict=True))
    with pytest.raises(ExtractTypeError):
      self.json_mapper.deserialize(location)

    location = make_location(['value'], '42.0', DecimalType(decimal.Decimal, strict=False))
    assert self.json_mapper.deserialize(location) == decimal.Decimal('42.0')

    location = make_location(['value'], '42.0', DecimalType(decimal.Decimal, strict=True))
    assert self.json_mapper.deserialize(location) == decimal.Decimal('42.0')

  def test_string_type(self):
    location = make_location(['a', 'b', 'c'], "foobar", StringType())
    assert self.json_mapper.deserialize(location) == "foobar"

    location = make_location(['a', 'b', 'c'], 42, StringType())
    with pytest.raises(ExtractTypeError) as excinfo:
      self.json_mapper.deserialize(location)
    assert str(excinfo.value.location.path) == '$.a.b.c'

    location = make_location(['a', 'b', 'c'], 42, StringType(strict=False))
    assert self.json_mapper.deserialize(location) == "42"

  def test_array_type(self):
    location = make_location(['a', 'b'], ["foo", "bar", "baz"], CollectionType(StringType()))
    assert self.json_mapper.deserialize(location) == ["foo", "bar", "baz"]

    location = make_location(['a', 'b'], ["foo", 42, "baz"], CollectionType(StringType()))
    with pytest.raises(ExtractTypeError) as excinfo:
      self.json_mapper.deserialize(location)
    assert str(excinfo.value.location.path) == '$.a.b[1]'

    location = make_location(['a', 'b'], ["foo", 42, "baz"], CollectionType(StringType(strict=False)))
    assert self.json_mapper.deserialize(location) == ["foo", "42", "baz"]

  def test_dict_type(self):
    location = make_location(['foo'], "Hello World!", ObjectType(StringType()))
    with pytest.raises(ExtractTypeError) as excinfo:
      self.json_mapper.deserialize(location)
    assert str(excinfo.value.location.path) == '$.foo'

    location = make_location(['foo'], {"msg": "Hello World!"}, ObjectType(StringType()))
    assert self.json_mapper.deserialize(location) == {"msg": "Hello World!"}

    typedef = CollectionType(ObjectType(StringType()))
    location = make_location(['root'], [{"a": "b"}, {"c": "d", "e": "f"}], typedef)
    assert self.json_mapper.deserialize(location) == [{"a": "b"}, {"c": "d", "e": "f"}]

    typedef = CollectionType(ObjectType(StringType()))
    location = make_location(['root'], [{"a": "b"}, {"c": 0.2, "e": "f"}], typedef)
    with pytest.raises(ExtractTypeError) as excinfo:
      self.json_mapper.deserialize(location)
    assert str(excinfo.value.location.path) == '$.root[1].c'

  def test_translate_type_def(self):
    assert isinstance(self.type_mapper.adapt(str), StringType)
    assert isinstance(self.type_mapper.adapt([str]), CollectionType)
    assert isinstance(self.type_mapper.adapt([str]).item_type, StringType)
    assert isinstance(self.type_mapper.adapt([]), CollectionType)
    assert isinstance(self.type_mapper.adapt([]).item_type, AnyType)
    assert isinstance(self.type_mapper.adapt({str}), ObjectType)
    assert isinstance(self.type_mapper.adapt({str}).value_type, StringType)

    with pytest.raises(InvalidTypeDefinitionError):
      self.type_mapper.adapt([str, str])

    assert isinstance(self.type_mapper.adapt(StringType), StringType)

    with pytest.raises(TypeError):
      self.type_mapper.adapt(CollectionType)  # not enough arguments

    typedef = CollectionType(StringType())
    assert self.type_mapper.adapt(typedef) is typedef

  def test_translate_type_def_typing(self):
    from typing import List, Dict
    assert isinstance(self.type_mapper.adapt(List[str]), CollectionType)
    assert isinstance(self.type_mapper.adapt(List[str]).item_type, StringType)
    assert isinstance(self.type_mapper.adapt(List), CollectionType)
    assert isinstance(self.type_mapper.adapt(List).item_type, AnyType)
    assert isinstance(self.type_mapper.adapt(Dict[str, str]), ObjectType)
    assert isinstance(self.type_mapper.adapt(Dict[str, str]).value_type, StringType)
    assert isinstance(self.type_mapper.adapt(Dict), ObjectType)
    assert isinstance(self.type_mapper.adapt(Dict).value_type, AnyType)
    with pytest.raises(InvalidTypeDefinitionError):
      print(self.type_mapper.adapt(Dict[int, str]))


class TestStruct(object):

  def setup_method(self, method):
    self.mapper = JsonObjectMapper()

  def test_struct(self):

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
      assert fields['telephone_numbers'].nullable

    from typing import List, Optional

    class Person(Struct):
      name = Field(str)
      age = Field(int, default=None)
      telephone_numbers = Field(List[str], nullable=True, default=lambda: [],
        options={'json_key': 'telephone-numbers'})

      class Meta:
        strict = True

    _test_object_def(Person)

    if sys.version >= '3.6':
      # TODO(nrosenstein): Just using globals()/locals() in the exec_() call
      #   does not work as expected, it cannot find the local variables then.
      scope = globals().copy()
      scope.update(locals())
      six.exec_(textwrap.dedent('''
        class Person(Struct):
          name: str
          age: int = None
          telephone_numbers: Optional[List[str]] = lambda: []
        _test_object_def(Person)
        '''), scope)

    payload = {'name': 'John Wick', 'telephone-numbers': ['+1 1337 38991']}
    expected = Person('John Wick', age=None, telephone_numbers=['+1 1337 38991'])
    assert deserialize(self.mapper, payload, Person) == expected

    payload = {'name': 'John Wick', 'age': 52}
    expected = Person('John Wick', age=52, telephone_numbers=[])
    assert deserialize(self.mapper, payload, Person) == expected

    payload = {'name': 'John Wick', 'age': None}
    expected = Person('John Wick', age=None, telephone_numbers=[])
    assert deserialize(self.mapper, payload, Person) == expected

    payload = {'name': 'John Wick', 'telephone_numbers': ['+1 1337 38991']}
    with pytest.raises(ExtractValueError) as excinfo:
     deserialize(self.mapper, payload, Person)
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
    assert deserialize(self.mapper, payload, [Person]) == expected

  def test_struct_equality(self):
    class Obj(Struct):
      a = Field(int)

    assert Obj(1) == Obj(1)
    assert not (Obj(1) == Obj(2))
    assert Obj(1) != Obj(2)
    assert not (Obj(1) != Obj(1))

  def test_struct_subclassing(self):

    class Person(Struct):
      name = Field(str)

    class Student(Person):
      student_id = Field(str)

    assert len(Student.__fields__) == 2
    assert list(Student.__fields__) == ['name', 'student_id']
    assert Student.__fields__['name'] is Person.__fields__['name']
    assert Student('John Wick', '4341115409').name == 'John Wick'
    assert Student('John Wick', '4341115409').student_id == '4341115409'

  def test_struct_def(self):
    class A(Struct):
      __fields__ = ['a', 'c', 'b']
    assert isinstance(A.__fields__, FieldSpec)
    assert list(A.__fields__.keys()) == ['a', 'c', 'b']
    assert A.__fields__['a'].datatype == AnyType()
    assert A.__fields__['c'].datatype == AnyType()
    assert A.__fields__['b'].datatype == AnyType()

    class B(Struct):
      __fields__ = [
        ('a', int),
        ('b', str, 'value')
      ]
    assert isinstance(B.__fields__, FieldSpec)
    assert list(B.__fields__.keys()) == ['a', 'b']
    assert B.__fields__['a'].datatype == IntegerType()
    assert B.__fields__['b'].datatype == StringType()

  def test_fieldspec_equality(self):
    assert FieldSpec() == FieldSpec()
    assert FieldSpec([Field(object, name='a')]) == FieldSpec([Field(object, name='a')])
    assert FieldSpec([Field(object, name='a')]) != FieldSpec([Field(object, name='b')])

  def test_fieldspec_update(self):

    class TestObject(Struct):
      test = Field(int)
      foo = Field(str)

    assert list(TestObject.__fields__.keys()) == ['test', 'foo']
    assert not hasattr(TestObject, 'test')
    assert not hasattr(TestObject, 'foo')
    assert TestObject.__fields__['foo'].name == 'foo'

    fields = [Field(str, name='test'), Field(object, name='bar')]
    TestObject.__fields__.update(fields)

    assert list(TestObject.__fields__.keys()) == ['test', 'foo', 'bar']
    assert not hasattr(TestObject, 'test')
    assert not hasattr(TestObject, 'foo')
    assert not hasattr(TestObject, 'bar')
    assert TestObject.__fields__['bar'].name == 'bar'

  def test_metadata_field(self):

    class Test(Struct):
      meta = MetadataField(str)
      value = Field(int)

      class Meta:
        strict = True

    assert Test('foo', 42).meta == 'foo'
    assert Test('foo', 42).value == 42

    data = {'meta': 'foo', 'value': 42}
    with pytest.raises(ExtractValueError) as excinfo:
      deserialize(self.mapper, data, Test)
    assert 'does not allow additional keys on extract' in str(excinfo.value)

    data = {'value': 42}
    assert deserialize(self.mapper, data, Test).meta is None
    assert deserialize(self.mapper, data, Test).value == 42

    class Map(dict):
      pass
    data = Map({'value': 42})
    data.__metadata__ = {'meta': 'foo'}
    assert deserialize(self.mapper, data, Test).meta == 'foo'
    assert deserialize(self.mapper, data, Test).value == 42

    # Test read function that doesn't add to handled_keys.

    def metadata_getter(locator, handled_keys):
      return locator.value.get('_metadata', {})

    Test.__fields__['meta'].metadata_getter = metadata_getter
    data = {'_metadata': {'meta': 'bar'}, 'value': 42}
    with pytest.raises(ExtractValueError) as excinfo:
      deserialize(self.mapper, data, Test)
    assert 'does not allow additional keys on extract' in str(excinfo.value)

    Test.Meta.strict = False
    assert deserialize(self.mapper, data, Test).meta == 'bar'
    assert deserialize(self.mapper, data, Test).value == 42

    # Test read function that _does_ add to handled_keys.

    def metadata_getter(locator, handled_keys):
      handled_keys.add('_metadata')  # allow even in _strict mode
      return locator.value.get('_metadata', {})

    Test.__fields__['meta'].metadata_getter = metadata_getter
    Test.Meta.strict = True
    data = {'_metadata': {'meta': 'bar'}, 'value': 42}
    assert deserialize(self.mapper, data, Test).meta == 'bar'
    assert deserialize(self.mapper, data, Test).value == 42

  def test_wildcard_field(self):
    class SomeTypeConfig(Struct):
      type = Field(str)
      options = WildcardField(str)

    x = SomeTypeConfig('foo', options=dict(message='Hello {}', name='Peter'))
    assert x.type == 'foo'
    assert x.options['message'] == 'Hello {}'
    assert x.options['name'] == 'Peter'

    y = deserialize(self.mapper, {'type': 'foo', 'message': 'Hello {}', 'name': 'Peter'}, SomeTypeConfig)
    assert x == y

  def test_objectkey_field(self):
    class Item(Struct):
      name = ObjectKeyField()
      value = Field(int)
    class Config(Struct):
      items = WildcardField(Item)

    x = Config(items={'a': Item('a', 42), 'b': Item('b', 99)})
    y = deserialize(self.mapper, {'a': {'value': 42}, 'b': {'value': 99}}, Config)
    assert x == y

  def test_custom_collection(self):

    class Items(CustomCollection, list):
      item_type = str
      def join(self):
        return ','.join(self)

    from nr.types.struct.struct.struct import _CustomCollectionMeta
    assert type(Items) == _CustomCollectionMeta
    assert Items.datatype == CollectionType(StringType(), Items)

    class Data(Struct):
      items = Field(Items)

    payload = {'items': ['a', 'b', 'c']}
    data = deserialize(self.mapper, payload, Data)
    assert data == Data(['a', 'b', 'c'])
    assert data.items.join() == 'a,b,c'

    assert Data(['a', 'b', 'c']).items.join() == 'a,b,c'

  def test_inline_schema_definition(self):
    # Test _InlineObjectTranslator
    datatype = DefaultTypeMapper().adapt({
      'a': Field(int),
      'b': Field(str),
    })
    assert type(datatype) == StructType
    assert sorted(datatype.struct_cls.__fields__.keys()) == ['a', 'b']

  def test_union_type(self):
    class Integer(Struct):
      __union_type_name__ = 'int'
      value = Field(int)
    class String(Struct):
      __union_type_name__ = 'string'
      value = Field(str)

    datatype = UnionType({'int': Integer, 'string': String})
    assert datatype == UnionType([Integer, String])

    assert deserialize(self.mapper, {'type': 'int', 'value': 42}, datatype) == Integer(42)
    assert deserialize(self.mapper, {'type': 'string', 'value': 'foo'}, datatype) == String('foo')
    with pytest.raises(ExtractTypeError):
      deserialize(self.mapper, {'type': 'int', 'value': 'foo'}, datatype)

    assert serialize(self.mapper, Integer(42), datatype) == {'type': 'int', 'value': 42}
    with pytest.raises(ExtractTypeError) as excinfo:
      serialize(self.mapper, 42, datatype)
    assert str(excinfo.value) == 'error in extract of value $: expected {Integer|String}, got int'

    from typing import Union
    assert datatype == DefaultTypeMapper().adapt(Union[Integer, String])

@pytest.mark.skip()
class CurrentlyDisabledTests(object):

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

  #class _GlobalNode(Struct):
  #  id = Field(str)
  #  children = Field([ForwardDecl('_GlobalNode')], default=list)

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
    locator = Locator.proxy(['a', 'b'])
    assert extract(locator.resolve(data), IntegerType(), locator) == 42
    with pytest.raises(ExtractTypeError):
      extract(locator.resolve(data), StringType(), locator)
    assert extract(locator.resolve(data), StringType(strict=False), locator) == '42'

  def test_inline_object_def_constructible():
    class MyObject(Object):
      myfield = Field({
        'a': Field(int),
        'b': Field(str)
      })

    assert issubclass(MyObject.myfield, Object)
    assert MyObject.myfield.__name__ == 'MyObject.myfield'

    obj = extract({'myfield': {'a': 0, 'b': 'foo'}}, MyObject)
    assert isinstance(obj.myfield, MyObject.myfield)
    assert obj.myfield.a == 0
    assert obj.myfield.b == 'foo'
    assert obj.myfield == MyObject.myfield(0, 'foo')
    assert obj == MyObject(obj.myfield)
    assert str(obj.myfield) == "MyObject.myfield(a=0, b='foo')"

  def test_collection():
    class Items(Collection, list):
      item_type = str

      def do_stuff(self):
        return ''.join(self)

    assert Items.datatype == ArrayType(StringType(), Items)

    items = extract(['a', 'b', 'c'], Items)
    assert items.do_stuff() == 'abc'
    assert store(items) == ['a', 'b', 'c']

  # Mixins

  def test_to_json():
    class Container(Object, ToJSON):
      data = Field(object)
    assert Container('abc').to_json() == {'data': 'abc'}
    assert Container([Container('abc')]).to_json() == {'data': [{'data': 'abc'}]}
    assert Container(b'42').to_json() == {'data': b'42'}
    assert Container(bytearray(b'42')).to_json() == {'data': bytearray(b'42')}

  def test_as_dict():
    class Container(Object, AsDict):
      data = Field(object)
    assert Container('abc').as_dict() == {'data': 'abc'}
    assert Container([Container('abc')]).as_dict() == {'data': [Container('abc')]}
    assert Container(b'42').as_dict() == {'data': b'42'}
    assert Container(bytearray(b'42')).as_dict() == {'data': bytearray(b'42')}

  def test_sequence():
    class Container(Object, Sequence):
      a = Field(object)
      b = Field(object)
    obj = Container(42, 'foo')
    assert obj.a == 42
    assert len(obj) == 2
    assert tuple(obj) == (42, 'foo')
    assert obj[0] == 42
    assert obj[1] == 'foo'

  def test_readme_example():
    Person = ForwardDecl('Person')
    People = translate_field_type({Person})
    class Person(Object):
      name = ObjectKeyField()
      age = Field(int)
      numbers = Field([str])

    data = {
      'John': {'age': 52, 'numbers': ['+1 123 5423435']},
      'Barbara': {'age': 29, 'numbers': ['+44 1523/5325323']}
    }
    people = extract(data, People)
    assert people['John'] == Person('John', 52, ['+1 123 5423435'])
    assert people['Barbara'] == Person('Barbara', 29, ['+44 1523/5325323'])

  #from nr.types.structured import *
  #from nr.types.structured.utils.yaml import load as load_yaml_with_metadata

  def test_add_origin_metadata_field():

    @utils.add_origin_metadata_field()
    class Item(Object):
      name = Field(str)

    class Config(Object):
      items = Field([Item])

    yaml_data = '''
      items:
        - name: foo
        - name: bar
        - name: baz
    '''

    data = load_yaml_with_metadata(yaml_data, filename='foobar.yaml')
    obj = extract(data, Config)

    assert obj.items[0].origin.filename == 'foobar.yaml'
    assert obj.items[1].origin.filename == 'foobar.yaml'
    assert obj.items[2].origin.filename == 'foobar.yaml'

    assert obj.items[0].origin.lineno == 3
    assert obj.items[1].origin.lineno == 4
    assert obj.items[2].origin.lineno == 5
