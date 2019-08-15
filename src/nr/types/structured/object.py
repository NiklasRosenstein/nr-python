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

import six
import sys
import typing

from nr.types import NotSet
from nr.types.interface import Interface, attr, default, implements, override
from nr.types.maps import OrderedDict
from nr.types.utils.typing import extract_optional
from .errors import ExtractTypeError, InvalidTypeDefinitionError
from .locator import Locator
from .types import IDataType, translate_field_type, DictType, StringType


class META:
  #: This the the name of the field that can be specified on the [[Object]]
  #: `Meta` class-level to define which fields are read from which parameters
  #: when the object is extracted from a nested structure.
  EXTRACT_MAPPING = 'extract_mapping'

  #: This is the name of the field that can be specified on the [[Object]]
  #: `Meta` class-level to define if extraction from a nested structure happens
  #: in a strict fashion. With this turned on, additional fields are not
  #: allowed. Defaults to off.
  EXTRACT_STRICT = 'strict'

  #: This field defines which fields are shown in the result of `__repr__()`
  #: for an [[Object]] subclass.
  REPR_FIELDS = 'repr_fields'


class IFieldDescriptor(Interface):
  """
  Interface that describes the behaviour of an [[Object]]'s field.
  """

  __INSTANCE_INDEX_COUNTER = 0

  #: The instance index is automatically assigned and is used to sort
  #: [[Object]] fields in the order they were created.
  instance_index = attr(int)

  #: The priority determines when the field will have its chance to
  #: extract values from the source dictionary. The default priority
  #: is zero (0).
  priority = attr(int)

  #: The name of the field represents the name of the attribute that is
  #: assigned to an [[Object]] instance.
  name = attr(typing.Optional[str])

  #: The datatype of the field. This represents the expected value that
  #: ends up in the object and usually represents the structure from
  #: which it can be extracted as well (but this is not the case for
  #: [[ObjectKeyField]] and [[WildcardField]]).
  datatype = attr(IDataType)

  #: If `True`, indicates that the field is derived from some other place.
  #: Usually this means that the field does not end up in the stored
  #: version of the [[Object]] the same way a standard [[Field]] does.
  derived = attr(bool)

  #: `True` if the field is required. This field has no default value and
  #: must be set by an implementation.
  required = attr(bool)

  def __init__(self):
    self.instance_index = IFieldDescriptor.__INSTANCE_INDEX_COUNTER
    IFieldDescriptor.__INSTANCE_INDEX_COUNTER += 1
    self.priority = 0
    self.name = None
    self.derived = False

  @default
  def bind(self, name):  # type: str -> None
    if self.name is not None:
      raise RuntimeError('cannot set field name to {!r}, name is already '
                         'set to {!r}'.format(name, self.name))
    self.name = name

  def get_default_value(self):  # type: () -> Any
    # raises: NotImplementedError
    pass

  def extract_kwargs(self, object_cls, locator, kwargs, handled_keys):
    # type: (Type[Object], Locator, Dict[str, Any], Set[str]) -> None
    """
    This method is called from the [[ObjectType.extract()]] method to
    compose the [[Object]] keyword arguments for construction.

    The field must specify the keys from [[Locator.value()]] that were
    treated in this method to prevent an error for an extract key if
    [[META.EXTRACT_STRICT]] is set.
    """


@implements(IFieldDescriptor)
class ObjectKeyField(object):
  """
  This [[IFieldDescriptor]] implementation represents a [[StringType]] field
  that extracts the key with which the object is defined in its parent
  structure.
  """

  def __init__(self):
    super(ObjectKeyField, self).__init__()
    self.required = True
    self.derived = True
    self.datatype = StringType()

  @override
  def get_default_value(self):
    raise NotImplementedError

  @override
  def extract_kwargs(self, object_cls, locator, kwargs, handled_keys):
    assert self.name not in kwargs, (self, object_cls, locator)
    kwargs[self.name] = locator.key()


@implements(IFieldDescriptor)
class WildcardField(object):
  """
  This [[IFieldDescriptor]] implementation consumes all extranous fields in
  a nested structure when an object is extracted and puts them into a map.
  """

  def __init__(self, value_type, only_matching_types=False):
    super(WildcardField, self).__init__()
    self.required = False
    self.derived = True
    self.value_type = translate_field_type(value_type)
    self.datatype = DictType(value_type)
    self.only_matching_types = only_matching_types

  @override
  def get_default_value(self):
    return {}

  @override
  def extract_kwargs(self, object_cls, locator, kwargs, handled_keys):
    assert self.name not in kwargs, (self, object_cls, locator)
    result = {}
    for key, value in six.iteritems(locator.value()):
      if key in handled_keys:
        continue
      if self.only_matching_types:
        try:
          value = locator.advance(key, value, self.value_type).extract()
        except ExtractTypeError:
          continue
      else:
        value = locator.advance(key, value, self.value_type).extract()
      result[key] = value
    handled_keys.update(result)
    kwargs[self.name] = result


@implements(IFieldDescriptor)
class Field(object):
  """
  This is the standard [[IFieldDescriptor]] implementation.
  """

  def __init__(self, datatype, nullable=False, required=None,
               default=NotSet, name=None):
    super(Field, self).__init__()
    if default is None:
      nullable = True
    if required is None:
      if default is NotSet:
        required = True
      else:
        required = False
    self.datatype = translate_field_type(datatype)
    self.nullable = nullable
    self.required = required
    self.default = default
    self.name = name

  def __repr__(self):
    return 'Field(datatype={!r}, nullable={!r}, default={!r})'.format(
      self.datatype, self.nullable, self.default)

  @override
  def get_default_value(self):
    if self.default is NotSet:
      raise RuntimeError('Field({!r}).default is NotSet'.format(self.name))
    if callable(self.default):
      return self.default()
    return self.default

  @override
  def extract_kwargs(self, object_cls, locator, kwargs, handled_keys):
    assert self.name not in kwargs, (self, object_cls, locator)
    renames = getattr(object_cls.Meta, META.EXTRACT_MAPPING, {})
    key = renames.get(self.name, self.name)
    if key not in locator.value():
      if self.required:
        locator.value_error('missing member "{}" for object of type "{}"'
                            .format(key, object_cls.__name__))
      return
    value = locator.value()[key]
    if self.nullable and value is None:
      kwargs[self.name] = None
    else:
      kwargs[self.name] = locator.advance(key, value, self.datatype).extract()
    handled_keys.add(key)


class FieldSpec(object):
  """
  Represents the fields of an [[Object]] with [[Field]] objects. Can be
  constructed from class member annotations or class members that have been
  assigned instances of the [[IFieldDescriptor]] class.
  """

  @classmethod
  def from_annotations(cls, obj_class):
    """
    Compiles a [[FieldSpec]] object from the class member annotations in
    the class *obj_class*. The annotation value is the field's datatype.
    If a value is assigned to the class member, it acts as the default value
    for that field.

    Type annotations can be wrapped in the [[Optional]] generic to indicate
    that the field is nullable. Alternatively, the default value of the field
    can be set to `None`.
    """

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
      fields.append((name, field))
    return cls(fields)

  @classmethod
  def from_class_members(cls, obj_class):
    """
    Compiles a [[FieldSpec]] object from the class members that implement the
    [[IFieldDescriptor]] interface.
    """

    fields = []
    for name, value in six.iteritems(vars(obj_class)):
      if not IFieldDescriptor.provided_by(value):
        continue
      if not value.name:
        value.bind(name)
      elif value.name != name:
        raise RuntimeError('mismatched field name {!r} != {!r}'
                           .format(value.name, name))
      fields.append((name, value))
    return cls(fields)

  @classmethod
  def merge(cls, field_a, fields_b):
    """
    Merge the fields of two [[FieldSpec]] objects into a single spec.
    """

    fields = field_a.all().copy()
    fields.update(fields_b.all())
    return cls(fields)

  def __init__(self, fields=()):
    if hasattr(fields, 'items') or hasattr(fields, 'iteritems'):
      fields = list(six.iteritems(fields))
    if not isinstance(fields, list):
      fields = list(fields)

    fields.sort(key=lambda x: x[1].instance_index)
    self.__all = OrderedDict(fields)

    fields.sort(key=lambda x: x[1].priority)  # relies on previous sort
    self.__by_priority = OrderedDict(fields)

    fields = [x for x in fields if not x[1].derived]
    self.__underived = OrderedDict(fields)

  def __getitem__(self, name):
    return self.__all[name]

  def __iter__(self):
    return iter(self.__all)

  def __len__(self):
    return len(self.__all)

  def __repr__(self):
    return 'FieldSpec({!r})'.format(self.__all)

  def __getattr__(self, name):
    return getattr(self.__all, name)

  def all(self):
    return self.__all

  def by_priority(self):
    return self.__by_priority

  def underived(self):
    return self.__underived


class _ObjectMeta(type):
  """
  Private. Meta class for the [[Object]] class. Handles the following things
  for [[Object]] subclasses:

    * Processes the field declarations and sets `__fields__`
    * Ensures `Meta` exists on the subclass
  """

  def __init__(self, name, bases, attrs):
    # Collect inherited fields.
    parent_fields = FieldSpec()
    for base in bases:
      if hasattr(base, '__fields__') and isinstance(base.__fields__, FieldSpec):
        parent_fields = FieldSpec.merge(parent_fields, base.__fields__)
    # If there are any class member annotations, we derive the object fields
    # from these rather than from class level [[Field]] objects.
    if hasattr(self, '__annotations__'):
      fields = FieldSpec.from_annotations(self)
    else:
      fields = FieldSpec.from_class_members(self)
    fields = FieldSpec.merge(parent_fields, fields)
    for key in fields:
      setattr(self, key, fields[key])
    self.__fields__ = fields

    if not hasattr(self, 'Meta'):
      class Meta:
        pass
      self.Meta = Meta


@six.add_metaclass(_ObjectMeta)
class Object(object):
  """
  An object is comprised of field descriptors and metadata which are used to
  build the object from a nested structure. Objects can be defined in two
  major ways: With the [[Field]] class, or with the class member annotation
  syntax that is available since Python 3.6.

  With annotations:

  ```py
  from typing import Optional
  class Person(Object):
    name: str
    age: Optional[int]
    telephone_numbers: [str] = lambda: []
  ```

  With the [[Field]] class:

  ```py
  class Person(Object):
    name = Field(str)
    age = Field(str, optional=True)
    telephone_numbers = Field([str], default=lambda: [])
  ```

  Both objects show the same semantics and can be deserialized from a
  this example YAML data:

  ```yaml
  people:
    - name: Barbara
    - name: John
      telephone_numbers:
        - "1 432 9876543"
    - name: Will
      age: 52
      telephone_numbers:
        - "1 234 5678912"
  ```
  """

  class Meta:
    pass

  __fields__ = FieldSpec()
  __location__ = None

  def __init__(self, *args, **kwargs):
    argcount = len(args) + len(kwargs)
    if argcount > len(self.__fields__):
      # TODO(nrosenstein): Include min number of args.
      raise TypeError('expected at max {} arguments, got {}'
                       .format(len(self.__fields__), argcount))

    # Add all arguments to the kwargs for extraction.
    for field, arg in zip(self.__fields__.values(), args):
      if field.name in kwargs:
        raise TypeError('duplicate arguments for "{}"'.format(field.name))
      kwargs[field.name] = arg

    # Extract all fields.
    handled_keys = set()
    for field in self.__fields__.by_priority().values():
      if field.name not in kwargs:
        if field.required:
          raise TypeError('missing required argument "{}"'.format(field.name))
        kwargs[field.name] = field.get_default_value()
      handled_keys.add(field.name)

    unhandled_keys = set(kwargs.keys()) - handled_keys
    if unhandled_keys:
      raise TypeError('unexpected keyword arguments: {!r}'.format(unhandled_keys))

    vars(self).update(kwargs)

  def __eq__(self, other):
    if type(other) != type(self):
      return False
    for key in self.__fields__:
      if getattr(self, key) != getattr(other, key):
        return False
    return True

  def __ne__(self, other):
    if type(other) == type(self):
      return True
    for key in self.__fields__:
      if getattr(self, key) == getattr(other, key):
        return False
    return True

  def __repr__(self):
    repr_fields = getattr(self.Meta, META.REPR_FIELDS, six.iterkeys(self.__fields__))
    attrs = ['{}={!r}'.format(k, getattr(self, k)) for k in repr_fields]
    return '{}({})'.format(type(self).__name__, ', '.join(attrs))


__all__ = [
  'IFieldDescriptor',
  'ObjectKeyField',
  'WildcardField',
  'Field',
  'FieldSpec',
  'Object'
]
