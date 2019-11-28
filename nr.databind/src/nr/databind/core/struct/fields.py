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

import functools
import six

from nr.collections import abc, OrderedDict
from nr.commons.notset import NotSet
from nr.commons.py import classdef, funcdef
from nr.commons.py.typing import extract_optional
from nr.stream import Stream
from ..datatypes import ObjectType, StringType, translate_type_def
from ..decoration import Decoration
from ..errors import SerializationTypeError, SerializationValueError
from ..interfaces import IDataType, Location


class StructField(object):
  """ Base class for struct fields. The *datatype* field will be translated
  to an [[IDatatype]] instance when it is processed by the [[_StructMeta]]
  class.

  Any positional arguments beyond the field's data-type must be #Decoration
  objects. Other arguments must be supplied as keyword-arguments. """

  classdef.repr('name datatype nullable')
  classdef.comparable('__class__ name datatype required')
  _INSTANCE_INDEX_COUNTER = 0

  def __init__(self, datatype, *decorations, **kwargs):
    """
    Parameters:
      datatype (IDataType): The data type for this field. Will be automatically
        translated via #translate_type_def().
      *decorations (Tuple[Decoration]): Decorations for this field.
        Decorations effectively represent options that can be understood by
        serializers/deserializers.
      name (Optional[str]): The name of the field. When a field is assigned to
        a #FieldSpec, the name will be automatically set.
      nullable (bool): Whether the value of this field is nullable (ie. can
        have a value of None, independent of its datatype).
    """

    if type(self) == StructField:
      raise RuntimeError('StructField cannot be instantiated directly.')

    name = kwargs.pop('name', None)
    assert name is None or isinstance(name, str), repr(name)
    nullable = kwargs.pop('nullable', False)
    funcdef.raise_kwargs(kwargs)

    if not IDataType.provided_by(datatype):
      datatype = translate_type_def(datatype)

    for item in decorations:
      if not isinstance(item, Decoration):
        raise TypeError('expected Decoration object, got {!r}'.format(
          type(item).__name__))

    self.datatype = datatype
    self.decorations = decorations
    self.name = name
    self.nullable = nullable

    self.instance_index = StructField._INSTANCE_INDEX_COUNTER
    StructField._INSTANCE_INDEX_COUNTER += 1

  def get_priority(self):  # type: () -> int
    """ The priority determines when the field will have its chance to
    extract values from the source dictionary. The default priority
    is zero (0). """

    return 0

  def is_derived(self):  # type: () -> bool
    """ Returns True if the field is a derived field and thus should be ignored
    when serializing the struct. """

    return False

  def set_name(self, name):  # type: str -> None
    """ Sets the name of the field. if the name is already set, a
    #RuntimeError will be raised. """

    if self.name is not None:
      raise RuntimeError('cannot set field name to {!r}, name is already '
                         'set to {!r}'.format(name, self.name))
    if not isinstance(name, str):
      raise TypeError('StructField.name must be a string, got {}'
                      .format(type(name).__name__))
    self.name = name

  def get_struct_class_member(self, struct_cls):  # type: (Type[Struct]) -> Any
    """ This method is called when the field is accessed via
    [[StructMeta.__getattr__()]] and can be used to expose a class-level
    property on the [[Struct]] class.

    Return [[NotSet]] if no property is to be exposed.

    The default implementation checks if the [[.datatype]] is an instance of
    [[StructType]] and returns the wrapped [[Struct]] subclass in that case.
    """

    if isinstance(self.datatype, StructType):
      return self.datatype.struct_cls
    return NotSet

  def get_default_value(self):  # type: () -> Any
    """ Return the default value for this field.
    Raises a #NotImplementedError if the field does not provide a default
    value. """

    raise NotImplementedError


class Field(StructField):
  """ The standard field implementation. """

  classdef.repr('name datatype nullable default')

  def __init__(self, datatype, *decorations, **kwargs):
    """
    Parameters:
      datatype (IDataType):
      *decorations:
      default (Any): The default value for the field. If the default value is
        callable, it will be called without arguments to retrieve the actual
        default value of the field.
      **kwargs: Additional keyword arguments supported by #StructField.
    """

    default = kwargs.pop('default', NotSet)
    nullable = kwargs.pop('nullable', NotSet)
    if default is None:
      if nullable is not NotSet and not nullable:
        raise ValueError('default cannot be None when nullable is False')
      nullable = True

    super(Field, self).__init__(datatype, nullable=nullable, **kwargs)
    self.default = default

  def get_default_value(self):
    if self.default is NotSet:
      raise RuntimeError('Field({!r}).default is NotSet'.format(self.name))
    if callable(self.default):
      return self.default()
    return self.default


class FieldSpec(object):
  """ A container for [[StructField]]s which is used to collect all fields of a
  [[Struct]] in a single place. """

  classdef.comparable('_fields')

  def __init__(self, fields=None):
    """ Creates a new [[FieldSpec]] object from a list of [[StructField]]
    objects. Note that all fields must have a name, otherwise a [[ValueError]]
    is raised. """

    fields = list(fields or [])
    for field in fields:
      if not isinstance(field, StructField):
        raise TypeError('expected StructField, got {!r}'
                        .format(type(field).__name__))
      if not field.name:
        raise ValueError('found unnamed field: {!r}'.format(field))
      assert isinstance(field.name, str), field

    fields.sort(key=lambda x: x.instance_index)

    self._fields = OrderedDict((x.name, x) for x in fields)
    self._fields_indexable = fields

  @classmethod
  def from_dict(cls, fields_dict):
    """ Compiles a [[FieldSpec]] from a dictionary that is expected to consist
    of only field definitions. Adapts Python type definitions to standard
    [[Field]] objects. [[StructField]]s in this dictionary that don't have a
    name will be assigned the name of their associated key. """

    fields = []
    for key, value in six.iteritems(fields_dict):
      if not isinstance(value, StructField):
        raise TypeError('expected StructField, key {!r} got {}'.format(
          key, type(value).__name__))
      if not value.name:
        value.name = key
      fields.append(value)
    return cls(fields)

  @classmethod
  def from_annotations(cls, obj_class):
    """ Compiles a [[FieldSpec]] object from the class member annotations in
    the class *obj_class*. The annotation value is the field's datatype.
    If a value is assigned to the class member, it acts as the default value
    for that field.

    Type annotations can be wrapped in the [[Optional]] generic to indicate
    that the field is nullable. Alternatively, the default value of the field
    can be set to `None`. """

    fields = []
    for name, datatype in six.iteritems(obj_class.__annotations__):
      wrapped_type = extract_optional(datatype)
      nullable = wrapped_type is not None
      default = getattr(obj_class, name, NotSet)
      field = Field(
        datatype=wrapped_type or datatype,
        nullable=nullable,
        default=default,
        name=name)
      fields.append(field)
    return cls(fields)

  @classmethod
  def from_class_members(cls, obj_class):
    """ Compiles a [[FieldSpec]] object from the class members that are subclasses
    of [[StructField]]. """

    fields = []
    for name, value in six.iteritems(vars(obj_class)):
      if not isinstance(value, StructField):
        continue
      if not value.name:
        value.name = name
      elif value.name != name:
        raise RuntimeError('mismatched field name {!r} != {!r}'
                           .format(value.name, name))
      fields.append(value)
    return cls(fields)

  @classmethod
  def from_list_def(cls, list_def):
    """ Compiles a FieldSpec from a list of tuples. Every tuple must have at
    least two elements, the first defining the name of the field, the second
    the type. An optional third field in the tuple may be used to specify
    the field default value. """

    assert not isinstance(list_def, abc.Mapping), "did not expect a mapping"

    fields = []
    for item in list_def:
      if isinstance(item, str):
        field = Field(object, name=item)
      elif isinstance(item, tuple):
        name, datatype = item[:2]
        default = item[2] if len(item) > 2 else NotSet
        field = Field(datatype, default=default, name=name)
        fields.append(field)
      elif isinstance(item, StructField):
        if not item.name:
          raise ValueError('unbound field in __fields__ list')
        field = item
      else:
        raise TypeError('expected {str, tuple, StructField}, got {!r}'
                        .format(type(item).__name__))
      fields.append(field)
    return cls(fields)

  def __getitem__(self, name):
    return self._fields[name]

  def __contains__(self, name):
    return name in self._fields

  def __iter__(self):
    return six.iterkeys(self._fields)

  def __len__(self):
    return len(self._fields)

  def __repr__(self):
    return 'FieldSpec({!r})'.format(list(self._fields.values()))

  def keys(self):  # type: () - >Stream[str]
    return Stream(six.iterkeys(self._fields))

  def values(self):  # type: () -> Stream[Field]
    return Stream(six.itervalues(self._fields))

  def items(self):  # type: () -> Stream[Tuple[str, Field]]
    return Stream(six.iteritems(self._fields))

  def update(self, fields):
    # type: (FieldSpec) -> FieldSpec
    """ Updates this [[FieldSpec]] with the files from another spec and returns
    *self*. This operation maintains the order of existing fields in the spec.
    """

    if not isinstance(fields, FieldSpec):
      fields = FieldSpec(fields)

    for key, value in fields._fields.items():
      self._fields[key] = value
    self._fields_indexable = list(self._fields.values())

    return self

  def get(self, key, default=None):
    return self._fields.get(key, default)

  def get_index(self, index):
    # type: (int) -> StructField
    return self._fields_indexable[index]


__all__ = [
  'StructField',
  'Field',
  'FieldSpec',
]
