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
from nr.types.structured.errors import InvalidTypeDefinitionError, ExtractTypeError
from nr.types.structured.core.mapper import Mapper
from nr.types.structured.core.datatypes import *
from nr.types.structured.interfaces import Path


def make_location(path, value=None, datatype=None):
  return Path(path).to_location(value, datatype)


class TestCore(object):

  def setup_method(self, method):
    self.mapper = Mapper()

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
    assert self.mapper.deserialize(proxy) == 42

  def test_decimal_type(self):
    location = make_location(['value'], '42.0', DecimalType(float, strict=False))
    assert self.mapper.deserialize(location) == pytest.approx(42.0)

    location = make_location(['value'], '42.0', DecimalType(float, strict=True))
    with pytest.raises(ExtractTypeError):
      self.mapper.deserialize(location)

    location = make_location(['value'], '42.0', DecimalType(decimal.Decimal, strict=False))
    assert self.mapper.deserialize(location) == decimal.Decimal('42.0')

    location = make_location(['value'], '42.0', DecimalType(decimal.Decimal, strict=True))
    assert self.mapper.deserialize(location) == decimal.Decimal('42.0')

  def test_string_type(self):
    location = make_location(['a', 'b', 'c'], "foobar", StringType())
    assert self.mapper.deserialize(location) == "foobar"

    location = make_location(['a', 'b', 'c'], 42, StringType())
    with pytest.raises(ExtractTypeError) as excinfo:
      self.mapper.deserialize(location)
    assert str(excinfo.value.location.path) == '$.a.b.c'

    location = make_location(['a', 'b', 'c'], 42, StringType(strict=False))
    assert self.mapper.deserialize(location) == "42"

  def test_array_type(self):
    location = make_location(['a', 'b'], ["foo", "bar", "baz"], CollectionType(StringType()))
    assert self.mapper.deserialize(location) == ["foo", "bar", "baz"]

    location = make_location(['a', 'b'], ["foo", 42, "baz"], CollectionType(StringType()))
    with pytest.raises(ExtractTypeError) as excinfo:
      self.mapper.deserialize(location)
    assert str(excinfo.value.location.path) == '$.a.b[1]'

    location = make_location(['a', 'b'], ["foo", 42, "baz"], CollectionType(StringType(strict=False)))
    assert self.mapper.deserialize(location) == ["foo", "42", "baz"]

  def test_dict_type(self):
    location = make_location(['foo'], "Hello World!", ObjectType(StringType()))
    with pytest.raises(ExtractTypeError) as excinfo:
      self.mapper.deserialize(location)
    assert str(excinfo.value.location.path) == '$.foo'

    location = make_location(['foo'], {"msg": "Hello World!"}, ObjectType(StringType()))
    assert self.mapper.deserialize(location) == {"msg": "Hello World!"}

    typedef = CollectionType(ObjectType(StringType()))
    location = make_location(['root'], [{"a": "b"}, {"c": "d", "e": "f"}], typedef)
    assert self.mapper.deserialize(location) == [{"a": "b"}, {"c": "d", "e": "f"}]

    typedef = CollectionType(ObjectType(StringType()))
    location = make_location(['root'], [{"a": "b"}, {"c": 0.2, "e": "f"}], typedef)
    with pytest.raises(ExtractTypeError) as excinfo:
      self.mapper.deserialize(location)
    assert str(excinfo.value.location.path) == '$.root[1].c'

  def test_translate_type_def(self):
    assert isinstance(self.mapper.translate_type_def(str), StringType)
    assert isinstance(self.mapper.translate_type_def([str]), CollectionType)
    assert isinstance(self.mapper.translate_type_def([str]).item_type, StringType)
    assert isinstance(self.mapper.translate_type_def([]), CollectionType)
    assert isinstance(self.mapper.translate_type_def([]).item_type, AnyType)
    assert isinstance(self.mapper.translate_type_def({str}), ObjectType)
    assert isinstance(self.mapper.translate_type_def({str}).value_type, StringType)

    with pytest.raises(InvalidTypeDefinitionError):
      self.mapper.translate_type_def([str, str])

    assert isinstance(self.mapper.translate_type_def(StringType), StringType)

    with pytest.raises(TypeError):
      self.mapper.translate_type_def(CollectionType)  # not enough arguments

    typedef = CollectionType(StringType())
    assert self.mapper.translate_type_def(typedef) is typedef

  def test_translate_type_def_typing(self):
    from typing import List, Dict
    assert isinstance(self.mapper.translate_type_def(List[str]), CollectionType)
    assert isinstance(self.mapper.translate_type_def(List[str]).item_type, StringType)
    assert isinstance(self.mapper.translate_type_def(List), CollectionType)
    assert isinstance(self.mapper.translate_type_def(List).item_type, AnyType)
    assert isinstance(self.mapper.translate_type_def(Dict[str, str]), ObjectType)
    assert isinstance(self.mapper.translate_type_def(Dict[str, str]).value_type, StringType)
    assert isinstance(self.mapper.translate_type_def(Dict), ObjectType)
    assert isinstance(self.mapper.translate_type_def(Dict).value_type, AnyType)
    with pytest.raises(InvalidTypeDefinitionError):
      print(self.mapper.translate_type_def(Dict[int, str]))


@pytest.mark.skip()
class TestSchema(object):

  def test_union_type(self):
    datatype = UnionType({'int': IntegerType(), 'string': StringType()})
    assert extract({'type': 'int', 'int': 42}, datatype) == UnionWrap(IntegerType(), 42)
    assert extract({'type': 'string', 'string': 'foo'}, datatype) == UnionWrap(StringType(), 'foo')
    with pytest.raises(ExtractValueError):
      extract({'type': 'int', 'string': 'foo'}, datatype)

  def test_inline_schema_definition(self):
    # Test _InlineObjectTranslator
    datatype = self.mapper.translate_type_def({
      'a': Field(int),
      'b': Field(str),
    })
    assert type(datatype) == ObjectType
    assert sorted(datatype.object_cls.__fields__.keys()) == ['a', 'b']
