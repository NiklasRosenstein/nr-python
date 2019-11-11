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
import typing

from nr.interface import implements
from nr.types.utils.typing import is_generic, get_generic_args
from .errors import InvalidTypeDefinitionError
from .mappers import BaseTypeMapper
from .interfaces import ITypeDefAdapter
from .datatypes import *


class DefaultTypeMapper(BaseTypeMapper):
  pass


@DefaultTypeMapper.register()
@implements(ITypeDefAdapter)
class PlainTypeTranslator(object):

  def adapt(self, mapper, py_type_def):
    if py_type_def is str:
      return StringType()
    elif py_type_def is int:
      return IntegerType()
    elif py_type_def is bool:
      return BooleanType()
    elif py_type_def is object:
      return AnyType()
    elif py_type_def in (float, decimal.Decimal):
      return DecimalType(py_type_def)
    raise InvalidTypeDefinitionError(py_type_def)


@DefaultTypeMapper.register()
@implements(ITypeDefAdapter)
class CollectionTranslator(object):

  def adapt(self, mapper, py_type_def):
    # []
    if isinstance(py_type_def, list) and len(py_type_def) == 0:
      return CollectionType(AnyType())
    # [<type>]
    elif isinstance(py_type_def, list) and len(py_type_def) == 1:
      return CollectionType(mapper.adapt(py_type_def[0]))
    # list
    elif py_type_def is list:
      return CollectionType(AnyType())
    # set
    elif py_type_def is set:
      return CollectionType(AnyType(), py_type=set)
    # typing.List
    elif is_generic(py_type_def, typing.List):
      item_type_def = get_generic_args(py_type_def)[0]
      if isinstance(item_type_def, typing.TypeVar):
        item_type_def = object
      return CollectionType(mapper.adapt(item_type_def))
    # typing.Set
    elif is_generic(py_type_def, typing.Set):
      item_type_def = get_generic_args(py_type_def)[0]
      if isinstance(item_type_def, typing.TypeVar):
        item_type_def = object
      return CollectionType(mapper.adapt(item_type_def), py_type=set)
    raise InvalidTypeDefinitionError(py_type_def)


@DefaultTypeMapper.register()
@implements(ITypeDefAdapter)
class ObjectTranslator(object):

  def adapt(self, mapper, py_type_def):
    # {}
    if isinstance(py_type_def, dict) and len(py_type_def) == 0:
      return ObjectType(AnyType())
    # {<type>}
    elif isinstance(py_type_def, set) and len(py_type_def) == 1:
      return ObjectType(mapper.adapt(next(iter(py_type_def))))
    # {'value_type': <type>}
    elif isinstance(py_type_def, dict) and len(py_type_def) == 1 and \
        'value_type' in py_type_def:
      return ObjectType(mapper.adapt(py_type_def['value_type']))
    # dict
    elif py_type_def is dict:
      return ObjectType(AnyType())
    # typing.Dict
    elif is_generic(py_type_def, typing.Dict):
      key_type_def, value_type_def = get_generic_args(py_type_def)
      if not isinstance(key_type_def, typing.TypeVar) and key_type_def is not str:
        raise InvalidTypeDefinitionError(py_type_def)
      if isinstance(value_type_def, typing.TypeVar):
        value_type_def = object
      return ObjectType(mapper.adapt(value_type_def))
    raise InvalidTypeDefinitionError(py_type_def)


__all__ = [
  'DefaultTypeMapper',
  'PlainTypeTranslator',
  'CollectionTranslator',
  'ObjectTranslator',
  'set_type_mapper',
]
