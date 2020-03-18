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

""" This module implements common helpers for dealing with decorations. """

from nr.databind.core import Decoration, IDataType
from nr.databind.core.datatypes import IntegerType, ObjectType, StringType, translate_type_def
from nr.pylang.utils import classdef


# Base classes for decorations.

class FieldDecoration(Decoration):
  " Base class for decorations of fields. "

  def attached(self, field):  # type: (Field) -> None
    " Called when a field decoration is attached to a field. "

    pass


class ClassDecoration(Decoration):
  """
  Base class for decorations of classes. Class instances can be used as
  decorators to add themselves to the `__decorations__` member of the class.
  Class decorations are not usually inherited unless #inheritable() is
  overwritten and returns #True.
  """

  def __call__(self, cls):  # type: (Type) -> Type
    """
    Add the decoration to *cls*. Creates a new `__decorations__` attribute
    if it does not exist on the class.
    """

    if '__decorations__' not in vars(cls):
      decorations = cls.__decorations__ = []
    else:
      decorations = cls.__decorations__
    decorations.append(self)
    return cls

  @classmethod
  def inheritable(cls):  # type: () -> bool
    return False

  @classmethod
  def get(cls, decorated_cls):  # type: (Type) -> Optional[ClassDecoration]
    """
    Returns the first instance of *cls* found in the decorations for the type
    object specified with *decorated_cls*. If #inheritable() returns True, the
    base classes of *decorated_cls* are searched as well.
    """

    if not isinstance(decorated_cls, type):
      raise TypeError('expected type instance, got {!r}'.format(type(decorated_cls).__name__))

    decoration = get_decoration(cls, vars(decorated_cls).get('__decorations__', []))
    if decoration is not None:
      return decoration

    if cls.inheritable():
      for base in decorated_cls.__bases__:
        decoration = cls.get(base)
        if decoration is not None:
          return decoration

    return None


class GlobalDecoration(Decoration):
  """
  Just a base class to indicate when a decoration can also be used globally.
  """


def get_decoration(decoration_cls, *decorations_lists):
  # type: (Type[Decoration], List[Decoration]) -> Optional[Decoration]
  """
  Given a #Decoration type object and zero or more lists of decorations, finds
  the first element that has the exact same type as *decoration_cls* and
  returns it.
  """

  for decorations in decorations_lists:
    for decoration in decorations:
      if type(decoration) is decoration_cls:
        return decoration

  return None


# Common concrete decorations.

class Collect(GlobalDecoration):
  """
  A global decoration that, if present, will be used to collect all nodes
  that are passed into #ObjectMapper.deserialize_node() or
  #ObjectMapper.serialize_node().
  """

  def __init__(self):
    self.nodes = []


class FieldName(FieldDecoration):
  """
  A decoration that indicates the name of the field for deserialization and
  serialization. Some serializers may subclass this decoration to allow
  granular overrides and fall back to this class if their subclass is not
  available.
  """

  def __init__(self, name):  # type: (str) -> None
    self.name = name

  def __repr__(self):
    return '{}(name={!r})'.format(type(self).__name__, self.name)


class Format(FieldDecoration):
  """
  A decoration that can be used to annotate the datatype of a field with
  formatting options that should be respected by the (de-) serializer if
  applicable.

  This is used commonly with the #DateType and #DatetimeType, in which case
  the format must be a string or an object with `parse()` and `format()`
  methods.
  """

  def __init__(self, *values):  # type: (Any) -> None
    self.values = values


class InheritKey(FieldDecoration):
  """
  This decoration is used for fields to indicate that during deserialization
  the value should be derived from the key that the #Struct was placed in. The
  datatype for fields with this decoration should be #IntegerType or #StringType.
  """

  def attached(self, field):
    if not isinstance(field.datatype, (IntegerType, StringType)):
      raise TypeError('Field({!r}).datatype should be IntegerType or StringType when decorated '
                      'with Key(), got {} instead.'.format(field.name,
                        field.datatype.to_human_readable()))


class Raw(FieldDecoration):
  """
  This that the field is filled with the raw value of the struct that it is
  deserialized from.
  """


class Remainder(FieldDecoration):
  """
  A decoration for fields to indicate that any unhandled fields during
  deserialization should be stored in that field. The datatype for fields with
  this decoration should be #ObjectType.
  """

  def attached(self, field):
    if not isinstance(field.datatype, ObjectType):
      raise TypeError('Field({!r}).datatype should be ObjectType when decorated with '
                      'Remainder(), got {} instead.'.format(field.name,
                        field.datatype.to_human_readable()))


class StoreNode(GlobalDecoration, ClassDecoration, FieldDecoration):
  """
  This decoration is used to have a deserializer store the #Node instance
  of a #Struct or #Collection in the resulting object's `__databind__`
  metadata under the "node" key.

  Note that this will create a cyclic reference as the #Node references
  the result and the result references the #Node.
  """


class SerializeAs(FieldDecoration, ClassDecoration):
  """
  A class and field decoration to indicate as what type it should be deserialized
  as and serialized to. This works well with interfaces to deserialize them as
  union types where every member of the union type implements said interface.
  """

  def __init__(self, datatype):  # type: (IDataType) -> None
    self.datatype = translate_type_def(datatype)


class Strict(GlobalDecoration, ClassDecoration):
  """
  This class decoration indicates that it should be deserialized in a strict
  fashion, resulting in a deserialization error if any unknown keys are
  encountered.
  """

  pass


class SkipDefaults(GlobalDecoration, FieldDecoration, ClassDecoration):
  """
  A decoration that indicates values in a #Struct that match the default values
  should be skipped during deserialization.
  """


class StaticFields(ClassDecoration):
  """
  A decoration for #Struct subclasses that overrides the way struct fields are
  exposed on the calss. When this decoration is present, the fields are exposed
  as their default value rather than the actual #Field object.
  """

  pass


class Validator(FieldDecoration, ClassDecoration):
  """
  A class and field decoration that specifies a function object or method name
  used to validate the deserialized result.
  """

  def __init__(self, function=None, method=None):
    # type: (Optional[Callable[[Any], None]], Optional[str]) -> None
    if (not function and not method) or (function and method):
      raise ValueError('need exactly one of the "function" or "method" arguments')
    self.function = function
    self.method = method
