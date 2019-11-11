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
Describes a strong typing system that can then be extracted from a structured
object.
"""

import decimal
import six

from nr.types import abc
from nr.interface import implements
from nr.types.utils import classdef
from .interfaces import IDataType


@implements(IDataType)
class AnyType(object):
  """
  Represents an arbitrary type. The "Any" datatype is simply ignored by
  converters.
  """

  classdef.comparable([])

  def check_value(self, py_value):
    return py_value


@implements(IDataType)
class BooleanType(object):

  classdef.comparable(['strict'])

  def __init__(self, strict=True):
    self.strict = strict

  def check_value(self, py_value):
    if self.strict and not isinstance(py_value, bool):
      raise TypeError('expected bool')
    return bool(py_value)


@implements(IDataType)
class StringType(object):

  classdef.comparable(['strict'])

  def __init__(self, strict=True):
    self.strict = strict

  def check_value(self, py_value):
    if isinstance(py_value, six.string_types):
      return py_value
    else:
      if self.strict:
        raise TypeError('expected string, got {}'.format(
          type(py_value).__name__))
      return str(py_value)


@implements(IDataType)
class IntegerType(object):

  classdef.comparable(['strict'])

  def __init__(self, strict=True):
    self.strict = strict

  def check_value(self, py_value):
    if isinstance(py_value, six.integer_types):
      return py_value
    else:
      if self.strict:
        raise TypeError('expected int')
      return int(py_value)


@implements(IDataType)
class DecimalType(object):
  """
  Represents a decimal value, backed by a float or [[decimal.Decimal]] object.
  If the selected Python type is Decimal, it will always accept strings which
  will be coerced to the correct type.

  If the selected type is float, it will only accept a string as input if
  *strict* is set to False.
  """

  classdef.comparable(['python_type', 'decimal_context', 'strict'])

  def __init__(self, python_type, decimal_context=None, strict=True):
    if python_type not in (float, decimal.Decimal):
      raise ValueError('python_type must be float or decimal.Decimal, got {!r}'
                       .format(python_type))
    if python_type is not decimal.Decimal and decimal_context:
      raise ValueError('decimal_context can only be used if python_type is '
                       'decimal.Decimal, but got {!r}'.format(python_type))
    self.python_type = python_type
    self.decimal_context = decimal_context
    self.strict = strict
    self.accepted_input_types = six.integer_types + (float, decimal.Decimal)
    if not self.strict or self.python_type is decimal.Decimal:
      self.accepted_input_types += six.string_types

  def coerce(self, value):
    if self.python_type is decimal.Decimal:
      return decimal.Decimal(value, self.decimal_context)
    elif self.python_type is float:
      return float(value)
    else:
      raise RuntimeError('python_type is invalid: {!r}'.format(
        self.python_type))

  def check_value(self, py_value):
    if not isinstance(py_value, self.accepted_input_types):
      raise TypeError('expected {}'.format(
        '|'.join(x.__name__ for x in self.accepted_input_types)))
    return self.coerce(py_value)


@implements(IDataType)
class CollectionType(object):
  """
  Represents a collection of elements. The *py_type* represents the type for
  representing the collection in Python. It may also be a function that
  processes the returned list.
  """

  classdef.comparable(['item_type', 'py_type'])

  def __init__(self, item_type, py_type=list):
    self.item_type = item_type
    self.py_type = py_type

  def check_value(self, py_value, _convert=True):
    if isinstance(py_value, six.string_types) \
        or not isinstance(py_value, abc.Iterable):
      raise TypeError('expected a collection type')
    if _convert and (not isinstance(self.py_type, type) or
        not isinstance(py_value, self.py_type)):
      py_value = self.py_type(py_value)
    return py_value


@implements(IDataType)
class ObjectType(object):
  """
  Represents an object (ie. a dictionary in Python lingo).
  """

  classdef.comparable(['value_type'])

  def __init__(self, value_type, py_type=dict):
    assert IDataType.provided_by(value_type), value_type
    self.value_type = value_type
    self.py_type = py_type

  def check_value(self, py_value, _convert=False):
    if not isinstance(py_value, abc.Mapping):
      raise TypeError('expected a mapping')
    if _convert and (not isinstance(self.py_type, type) or
        not isinstance(py_value, self.py_type)):
      py_value = self.py_type(py_value)
    return py_value


__all__ = [
  'AnyType',
  'BooleanType',
  'StringType',
  'IntegerType',
  'DecimalType',
  'CollectionType',
  'ObjectType',
]
