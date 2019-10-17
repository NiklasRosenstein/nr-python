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
from nr.types.structured.struct import CustomCollection, Field, Struct, StructType, deserialize
from nr.types.structured.core import (Path, DefaultTypeMapper,
  ExtractTypeError, ExtractValueError, InvalidTypeDefinitionError,
  JsonObjectMapper)
from nr.types.structured.core.datatypes import *


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

  def test_custom_collection(self):

    class Items(CustomCollection, list):
      item_type = str
      def join(self):
        return ','.join(self)

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


@pytest.mark.skip()
class CurrentlyDisabledTests(object):

  def test_union_type(self):
    datatype = UnionType({'int': IntegerType(), 'string': StringType()})
    assert extract({'type': 'int', 'int': 42}, datatype) == UnionWrap(IntegerType(), 42)
    assert extract({'type': 'string', 'string': 'foo'}, datatype) == UnionWrap(StringType(), 'foo')
    with pytest.raises(ExtractValueError):
      extract({'type': 'int', 'string': 'foo'}, datatype)
