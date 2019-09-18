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
import inspect
import six
import sys
import typing

from .errors import InvalidTypeDefinitionError
from nr.types import abc
from nr.types.interface import (
  Interface,
  default,
  implements,
  override,
  staticattr)
from nr.types.utils import classdef
from nr.types.utils.typing import is_generic, get_generic_args

getargspec = getattr(
  __import__('inspect'), 'getargspec' if six.PY2 else 'getfullargspec')

#: A message sent to [[IDataType]] instances when the datatype is attached to
#: a field, which in turn is attached to an [[Object]]. The message data is
#: a dictionary of the object and field name.
MSG_PROPAGATE_FIELDNAME = 'MSG_PROPAGATE_FIELDNAME'


class IDataType(Interface):
  """
  Interface that describes a datatype.
  """

  classdef.hashable_on([])  # adds __hash__, __eq__, __ne__ to the interface

  @default
  def __repr__(self):
    # This default implementation tries to produce a sensible string
    # representation that is applicable to common implementations.
    spec = getargspec(type(self).__init__)
    no_kw_count = len(spec.args) - len(spec.defaults or [])
    parts = []
    parts += [str(getattr(self, k)) for k in spec.args[1:no_kw_count]]
    parts += ['{}={!r}'.format(k, getattr(self, k)) for k in spec.args[no_kw_count:]]
    return '{}({})'.format(type(self).__name__, ', '.join(parts))

  @default
  def human_readable(self):
    return repr(self)

  @default
  def child_datatypes(self):  # type: () -> Iterable[IDataType]
    return ()

  @default
  def message(self, message_type, data):  # type: () -> Optional[bool]
    for child in self.child_datatypes():
      result = child.message(message_type, data)
      if result is False:
        return False

  def extract(self, locator):  # type: (Locator) -> Any
    pass

  def store(self, locator):  # type: (Locator) -> Any
    pass


@implements(IDataType)
class AnyType(object):

  classdef.hashable_on([])

  @override
  def extract(self, locator):
    return locator.value()

  @override
  def store(self, locator):
    return locator.value()


@implements(IDataType)
class BooleanType(object):

  classdef.hashable_on([])

  @override
  def extract(self, locator):
    if isinstance(locator.value(), bool):
      return locator.value()
    locator.type_error()

  store = extract


@implements(IDataType)
class StringType(object):
  """
  Represents a string value.
  """

  classdef.hashable_on(['strict'])

  def __init__(self, strict=True):
    self.strict = strict

  @override
  def extract(self, locator):
    if isinstance(locator.value(), six.string_types):
      return locator.value()
    if self.strict:
      locator.type_error()
    return str(locator.value())

  @override
  def store(self, locator):
    return locator.value()


@implements(IDataType)
class IntegerType(object):
  """
  Represents an integer value.
  """

  classdef.hashable_on(['strict'])

  def __init__(self, strict=True):
    self.strict = strict

  @override
  def extract(self, locator):
    if not self.strict and isinstance(locator.value(), six.string_types):
      try:
        return int(locator.value())
      except ValueError as exc:
        locator.value_error(exc)
    if isinstance(locator.value(), int):
      return locator.value()
    locator.type_error()

  @override
  def store(self, locator):
    return locator.value()


@implements(IDataType)
class DecimalType(object):
  """
  Represents a decimal value, which can be represented by a float or
  [[decimal.Decimal]] object. If the selected Python type is Decimal, it
  will always accept strings as input.

  If the selected type is `float`, it will only accept a string as input if
  *strict* is set to `False`.
  """

  classdef.hashable_on(['python_type', 'decimal_context', 'strict'])

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

  def coerce(self, value):
    if self.python_type is decimal.Decimal:
      return decimal.Decimal(value, self.decimal_context)
    elif self.python_type is float:
      return float(value)
    else:
      raise RuntimeError('python_type is invalid: {!r}'
                         .format(self.python_type))

  def accepted_input_types(self):
    types = (int, float, decimal.Decimal)
    if not self.strict or self.python_type is decimal.Decimal:
      types += (str,)
    return types

  @override
  def extract(self, locator):
    value = locator.value()
    if isinstance(value, self.accepted_input_types()):
      return self.coerce(value)
    locator.type_error()

  @override
  def store(self, value):
    # TODO(@NiklasRosenstein): Can we make it decidable by the user if the
    #   serialization library supports [[decimal.Decimal]]?
    return float(value)


@implements(IDataType)
class ArrayType(object):
  """
  Represents an array type.
  """

  BASIC_SEQUENCE_TYPES = (list, tuple, set)

  classdef.hashable_on(['item_type', 'py_type', 'store_type'])

  def __init__(self, item_type, py_type=list, store_type=list):
    self.item_type = item_type
    self.py_type = py_type
    self.store_type = store_type

  @override
  def child_datatypes(self):
    yield self.item_type

  @override
  def extract(self, locator):
    if not isinstance(locator.value(), self.BASIC_SEQUENCE_TYPES):
      locator.type_error()
    result = []
    for index, item in enumerate(locator.value()):
      item = locator.advance(index, item, self.item_type).extract()
      result.append(item)
    if not isinstance(self.py_type, type) or not isinstance(result, self.py_type):
      result = self.py_type(result)
    return result

  @override
  def store(self, locator):
    result = []
    for index, item in enumerate(locator.value()):
      item = locator.advance(index, item, self.item_type).store()
      result.append(item)
    if not isinstance(self.store_type, type) or not isinstance(result, self.store_type):
      result = self.store_type(result)
    return result


@implements(IDataType)
class DictType(object):
  """
  Represents an object type.
  """

  BASIC_DICTIONARY_TYPES = (dict,)

  classdef.hashable_on(['value_type'])

  def __init__(self, value_type):
    assert IDataType.provided_by(value_type), value_type
    self.value_type = value_type

  @override
  def child_datatypes(self):
    yield self.value_type

  @override
  def extract(self, locator):
    if not isinstance(locator.value(), self.BASIC_DICTIONARY_TYPES):
      locator.type_error()
    result = {}
    for key in locator.value():
      value = locator.advance(key, locator.value()[key], self.value_type).extract()
      result[key] = value
    return result

  @override
  def store(self, locator):
    result = {}
    for key in locator.value():
      value = locator.advance(key, locator.value()[key], self.value_type).store()
      result[key] = value
    return result


@implements(IDataType)
class ObjectType(object):
  """
  Represents the datatype for an [[Object]] subclass.
  """

  classdef.hashable_on(['object_cls'])

  def __init__(self, object_cls):
    assert isinstance(object_cls, type), object_cls
    assert issubclass(object_cls, Object), object_cls
    self.object_cls = object_cls

  @override
  def extract(self, locator):
    if not isinstance(locator.value(), abc.Mapping):
      locator.type_error()

    fields = self.object_cls.__fields__
    renames = getattr(self.object_cls.Meta, META.EXTRACT_MAPPING, {})
    strict = getattr(self.object_cls.Meta, META.EXTRACT_STRICT, False)

    kwargs = {}
    handled_keys = set()
    for name, field in fields.items().sortby(lambda x: x[1].priority):
      assert name == field.name, "woops: {}".format((name, field))
      field.extract_kwargs(self.object_cls, locator, kwargs, handled_keys)

    if strict:
      remaining_keys = set(locator.value().keys()) - handled_keys
      if remaining_keys:
        locator.value_error('strict object type "{}" does not allow '
                            'additional keys on extract, but found {!r}'
                            .format(self.object_cls.__name__, remaining_keys))

    obj = object.__new__(self.object_cls)
    obj.__location__ = locator.location_info()
    try:
      obj.__init__(**kwargs)
    except TypeError as exc:
      raise locator.type_error(exc)
    return obj

  @override
  def store(self, locator):
    if not isinstance(locator.value(), self.object_cls):
      locator.type_error()
    result = {}
    for name, field in self.object_cls.__fields__.items():
      value = getattr(locator.value(), name)
      result[field.name] = locator.advance(name, value, field.datatype).store()
    return result

  @override
  def message(self, message_type, data):
    if message_type == MSG_PROPAGATE_FIELDNAME:
      if self.object_cls.__name__ == _InlineObjectTranslator.GENERATED_TYPE_NAME:
        self.object_cls.__name__ = data
    return IDataType['message'](self, message_type, data)


class UnionWrap(object):
  """
  Wraps the value of a Union field.
  """

  classdef.hashable_on(['datatype', 'value'])
  classdef.def_repr(['datatype', 'value'])

  def __init__(self, datatype, value):
    self.datatype = datatype
    self.value = value


@implements(IDataType)
class UnionType(object):
  """
  A union datatype that expects an object with a "type" key as well as a
  key that has the name of the specified type.
  """

  classdef.hashable_on(['mapping', 'strict', 'type_key'])

  def __init__(self, mapping, strict=True, type_key='type'):  # type: (Dict[str, IDataType], str, bool) -> None
    self.mapping = {k: translate_field_type(v) for k, v in mapping.items()}
    self.type_key = type_key

  @override
  def child_datatypes(self):
    return self.mapping.values()

  @override
  def extract(self, locator):
    if not isinstance(locator.value(), abc.Mapping):
      locator.type_error()
    if self.type_key not in locator.value():
      locator.type_error()
    type_name = locator.value()[self.type_key]
    if type_name not in locator.value():
      locator.value_error('missing "{}" key'.format(type_name))
    for key in locator.value():
      if key not in (self.type_key, type_name):
        locator.value_error('extra key "{}"'.format(key))
    if type_name not in self.mapping:
      locator.value_error('unexpected "{}": "{}"'.format(self.type_key, type_name))
    datatype = self.mapping[type_name]
    value = locator.advance(type_name, locator.value()[type_name], datatype).extract()
    return UnionWrap(datatype, value)

  @override
  def store(self, locator):
    type_name = locator.value()[self.type_key]
    datatype = self.mapping[type_name]
    return {
      self.type_key: type_name,
      type_name: locator.advance(type_name, locator.value()[type_name], datatype).store()
    }


@implements(IDataType)
class ForwardDecl(object):
  """
  Allows you to forward-declare a type in the current namespace. This is
  necessary for [[Object]]s that reference each other. The type will
  be resolved on-demand.

  Example:

  ```py
  class Wheel(Object):
    car: ForwardDecl('Car')

  class Car(Object):
    wheels: List[Wheel]
  ```
  """

  classdef.hashable_on(['name', 'frame'])

  def __init__(self, name, frame=None):
    self.name = name
    self.frame = frame or sys._getframe(1)

  def __repr__(self):
    return 'ForwardDecl({!r} in {!r})'.format(self.name, self.frame.f_code.co_filename)

  def resolve(self):
    for mapping in [self.frame.f_locals, self.frame.f_globals]:
      if self.name in mapping:
        x = mapping[self.name]
        break
    else:
      raise RuntimeError('{} could not be resolved'.format(self))
    return translate_field_type(x)

  @override
  def extract(self, locator):
    return self.resolve().extract(locator)

  @override
  def store(self, locator):
    return self.resolve().store(locator)


@implements(IDataType)
class PythonType(object):
  """
  Represents a Python type. No serialize/deserialize capabilities.
  """

  classdef.hashable_on(['py_type'])

  def __init__(self, py_type):
    assert isinstance(py_type, type)
    self.py_type = py_type

  @override
  def extract(self, locator):
    raise RuntimeError('{!r} cannot be extracted')

  @override
  def store(self, locator):
    raise RuntimeError('{!r} cannot be stored')


class IFieldTypeTranslator(Interface):
  """
  Interface for type translators, taking arbitrary Python objects and
  translating them to proper type definitions.
  """

  priority = staticattr(0)

  @staticmethod
  def translate(self, py_type_def):  # type: Any -> IDataType
    # raise: InvalidTypeDefinitionError
    pass


@implements(IFieldTypeTranslator)
class _PlainTypeTranslator(object):

  @override
  @staticmethod
  def translate(py_type_def):
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


@implements(IFieldTypeTranslator)
class _ArrayTranslator(object):

  @override
  @staticmethod
  def translate(py_type_def):
    # []
    if isinstance(py_type_def, list) and len(py_type_def) == 0:
      return ArrayType(AnyType())
    # [<type>]
    elif isinstance(py_type_def, list) and len(py_type_def) == 1:
      return ArrayType(translate_field_type(py_type_def[0]))
    # list
    elif py_type_def is list:
      return ArrayType(AnyType())
    # set
    elif py_type_def is set:
      return ArrayType(AnyType(), py_type=set)
    # typing.List
    elif is_generic(py_type_def, typing.List):
      item_type_def = get_generic_args(py_type_def)[0]
      if isinstance(item_type_def, typing.TypeVar):
        item_type_def = object
      return ArrayType(translate_field_type(item_type_def))
    # typing.Set
    elif is_generic(py_type_def, typing.Set):
      item_type_def = get_generic_args(py_type_def)[0]
      if isinstance(item_type_def, typing.TypeVar):
        item_type_def = object
      return ArrayType(translate_field_type(item_type_def), py_type=set)
    raise InvalidTypeDefinitionError(py_type_def)


@implements(IFieldTypeTranslator)
class _CollectionTranslator(object):

  @override
  @staticmethod
  def translate(py_type_def):
    # {}
    if isinstance(py_type_def, dict) and len(py_type_def) == 0:
      return DictType(AnyType())
    # {<type>}
    elif isinstance(py_type_def, set) and len(py_type_def) == 1:
      return DictType(translate_field_type(next(iter(py_type_def))))
    # dict
    elif py_type_def is dict:
      return DictType(AnyType())
    # typing.Dict
    elif is_generic(py_type_def, typing.Dict):
      key_type_def, value_type_def = get_generic_args(py_type_def)
      if not isinstance(key_type_def, typing.TypeVar) and key_type_def is not str:
        raise InvalidTypeDefinitionError(py_type_def)
      if isinstance(value_type_def, typing.TypeVar):
        value_type_def = object
      return DictType(translate_field_type(value_type_def))
    raise InvalidTypeDefinitionError(py_type_def)


@implements(IFieldTypeTranslator)
class _ForwardDeclTranslator(object):

  @override
  @staticmethod
  def translate(py_type_def):
    if isinstance(py_type_def, ForwardDecl):
      return py_type_def
    raise InvalidTypeDefinitionError(py_type_def)


@implements(IFieldTypeTranslator)
class _ObjectAndCollectionTranslator(object):

  @override
  @staticmethod
  def translate(py_type_def):
    if isinstance(py_type_def, type) and issubclass(py_type_def, Object):
      return ObjectType(py_type_def)
    elif isinstance(py_type_def, type) and issubclass(py_type_def, Collection):
      return py_type_def.datatype
    raise InvalidTypeDefinitionError(py_type_def)


@implements(IFieldTypeTranslator)
class _InlineObjectTranslator(object):
  """
  Implements the translation of inline object definitons in dictionary form.
  Example:

  ```py
  datatype = translate_field_type({
    'a': Field(int),
    'b': Field(str),
  })
  assert type(datatype) == ObjectType
  assert sorted(datatype.object_cls.__fields__.keys()) == ['a', 'b']
  ```
  """

  GENERATED_TYPE_NAME = '_InlineObjectTranslator_generated'

  @override
  @classmethod
  def translate(cls, py_type_def):
    if isinstance(py_type_def, dict):
      return ObjectType(type(cls.GENERATED_TYPE_NAME, (Object,), py_type_def))
    raise InvalidTypeDefinitionError(py_type_def)


@implements(IFieldTypeTranslator)
class _ProxyTranslator(object):

  @override
  @classmethod
  def translate(cls, py_type_def):
    if isinstance(py_type_def, str):
      return ForwardDecl(py_type_def, cls._find_reference_frame())
    raise InvalidTypeDefinitionError(py_type_def)

  @staticmethod
  def _find_reference_frame():
    # TODO(@NiklasRosenstein)
    pass


@implements(IFieldTypeTranslator)
class _PythonTypeTranslator(object):

  priority = -1000

  @override
  @classmethod
  def translate(cls, py_type_def):
    if isinstance(py_type_def, type) and py_type_def.__module__ != 'typing':
      return PythonType(py_type_def)
    raise InvalidTypeDefinitionError(py_type_def)


def translate_field_type(py_type_def):  # type: (Any) -> IDataType
  """
  Translates a Python type declaration to an [[IDataType]] object. If the
  translation fails, a [[InvalidTypeDefinitionError]] is raised.

  All implementations of the [[IFieldTypeTranslator]] interface are asked
  to translate the type definition until the first matches.
  """

  if IDataType.provided_by(py_type_def):
    return py_type_def
  elif isinstance(py_type_def, type) and IDataType.implemented_by(py_type_def):
    return py_type_def()
  # NOTE(@NiklasRosenstein): Potential perf improvement by caching sorted implementations.
  implementations = IFieldTypeTranslator.implementations()
  for impl in sorted(implementations, key=lambda x: x.priority):
    try:
      return impl.translate(py_type_def)
    except InvalidTypeDefinitionError:
      pass
  raise InvalidTypeDefinitionError(py_type_def)


from .locator import Locator
from .object import Object, META
from .collection import Collection


__all__ = [
  'IDataType',
  'AnyType',
  'BooleanType',
  'StringType',
  'IntegerType',
  'DecimalType',
  'ArrayType',
  'DictType',
  'ObjectType',
  'UnionType',
  'UnionWrap',
  'ForwardDecl',
  'IFieldTypeTranslator',
  'translate_field_type',
]
