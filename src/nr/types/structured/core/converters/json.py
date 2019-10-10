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

"""
Converts from and to JSON like nested structures.
"""

import decimal
import six

from nr.types.collections import OrderedDict
from nr.types.interface import implements
from ..errors import ExtractTypeError
from ..interfaces import IConverter
from ..datatypes import *


@implements(IConverter)
class AnyConverter(object):

  namespace = 'json'

  def accept(self, datatype):
    return type(datatype) == AnyType

  def deserialize(self, mapper, location):
    return location.value

  def serialize(self, mapper, location):
    return location.value


@implements(IConverter)
class BooleanConverter(object):

  namespace = 'json'

  def accept(self, datatype):
    return type(datatype) == BooleanType

  def deserialize(self, mapper, location):
    if isinstance(location.value, bool):
      return location.value
    raise ExtractTypeError(location)

  def serialize(self, mapper, location):
    if location.datatype.strict and not isinstance(location.value, bool):
      raise ExtractTypeError(location)
    return bool(location.value)


@implements(IConverter)
class StringConverter(object):

  namespace = 'json'

  def accept(self, datatype):
    return type(datatype) == StringType

  def deserialize(self, mapper, location):
    if isinstance(location.value, six.string_types):
      return location.value
    if location.datatype.strict:
      raise ExtractTypeError(location)
    return str(location.value)

  def serialize(self, mapper, location):
    return location.value


@implements(IConverter)
class IntegerConverter(object):

  namespace = 'json'

  def accept(self, datatype):
    return type(datatype) == IntegerType

  def deserialize(self, mapper, location):
    return location.value

  def serialize(self, mapper, location):
    return location.value


@implements(IConverter)
class DecimalConverter(object):

  namespace = 'json'

  def __init__(self, supports_decimal=False, as_string=False):
    super(DecimalConverter, self).__init__()
    self.supports_decimal = supports_decimal
    self.as_string = as_string

  def accept(self, datatype):
    return type(datatype) == DecimalType

  def deserialize(self, mapper, location):
    if isinstance(location.value, location.datatype.accepted_input_types):
      return location.datatype.coerce(location.value)
    raise ExtractTypeError(location)

  def serialize(self, mapper, location):
    if self.as_string:
      return str(location.value)
    if self.supports_decimal and isinstance(location, decimal.Decimal):
      return location.value
    return float(location.value)


@implements(IConverter)
class CollectionConverter(object):
  """
  Serializes the [[CollectionType]] from a Python collection object to a
  list (for serialization in JSON). If the underlying Python type is
  unordered, the values will be sorted by their hash.
  """

  namespace = 'json'

  def __init__(self, json_type=list):
    super(CollectionConverter, self).__init__()
    self.json_type = json_type

  def accept(self, datatype):
    return type(datatype) == CollectionType

  def deserialize(self, mapper, location):
    # Check if the value we receive is actually a collection.
    try:
      location.datatype.check_value(location.value, _convert=False)
    except TypeError:
      raise ExtractTypeError(location)

    # Deserialize child elements.
    item_type = location.datatype.item_type
    result = []
    for index, item in enumerate(location.value):
      item_location = location.sub(index, item, item_type)
      result.append(mapper.deserialize(item_location))

    # Convert to the designated Python type.
    py_type = location.datatype.py_type
    if not isinstance(py_type, type) or not isinstance(result, py_type):
      result = py_type(result)

    return result

  def serialize(self, mapper, location):
    # Check if the value we receive is actually a collection.
    try:
      location.datatype.check_value(location.value, _convert=False)
    except TypeError:
      raise ExtractTypeError(location)

    # Serialize child elements.
    item_type = location.datatype.item_type
    result = []
    for index, item in enumerate(location.value):
      item_location = location.sub(index, item, item_type)
      result.append(mapper.serialize(item_location))

    # Convert to the designated JSON type.
    json_type = self.json_type
    if not isinstance(json_type, type) or not isinstance(result, json_type):
      result = json_type(result)

    return result


@implements(IConverter)
class ObjectConverter(object):

  namespace = 'json'

  def __init__(self, json_type=OrderedDict):
    super(ObjectConverter, self).__init__()
    self.json_type = json_type

  def accept(self, datatype):
    return type(datatype) == ObjectType

  def deserialize(self, mapper, location):
    if not isinstance(location.value, dict):
      raise ExtractTypeError(location)
    value_type = location.datatype.value_type
    result = location.datatype.py_type()
    for key in location.value:
      item_location = location.sub(key, location.value[key], value_type)
      result[key] = mapper.deserialize(item_location)
    return result

  def serialize(self, mapper, location):
    result = self.json_type()
    for key in location.value:
      item_location = location.sub(key, location.value[key], value_type)
      result[key] = mapper.serialize(item_location)
    return result
