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

from nr.types.abc import Mapping
from nr.types.collections import OrderedDict
from nr.types.interface import Interface, attr, default, implements, override
from nr.types.singletons import NotSet
from nr.types.stream import Stream
from nr.types.utils import classdef
from nr.types.utils.typing import extract_optional
from .errors import ExtractTypeError, InvalidTypeDefinitionError
from .locator import Locator
from .types import (
  MSG_PROPAGATE_FIELDNAME,
  IDataType,
  DictType,
  StringType,
  ObjectType,
  translate_field_type)


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

  classdef.hashable_on('priority name datatype derived required',
                       decorate=default)

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
    if not isinstance(name, str):
      raise TypeError('IFieldDescriptor.name must be a string, got {}'
                      .format(type(name).__name__))
    self.name = name

  @default
  def get_class_member_value(self, object_cls):  # type: (Type[Object]) -> Any
    """
    This method is called when the field is accessed via
    [[Object.__getattr__()]] and can be used to expose a class-level property
    on the [[Object]] class.

    Return [[NotSet]] if no property is to be exposed.

    The default implementation checks if the [[.datatype]] is an instance of
    [[ObjectType]] and returns the wrapped [[Object]] subclass in that case.
    """

    if isinstance(self.datatype, ObjectType):
      return self.datatype.object_cls
    return NotSet

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
    self.datatype = DictType(self.value_type)
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
    assert name is None or isinstance(name, str), repr(name)
    self.name = name

  def __repr__(self):
    return 'Field(datatype={!r}, nullable={!r}, default={!r}, name={!r})'\
      .format(self.datatype, self.nullable, self.default, self.name)

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


@implements(IFieldDescriptor)
class MetadataField(Field):
  """
  Represents a field which, on extract, is read from metadata that is
  present on the object from which the field is being extract.

  There are two things that can be configured to how the metadata is read:

  * The `metadata_getter` to get the metadata container (defined as a
    parameter to the field, or otherwise retrieved from the options passed
    to [[extract()]]). The [[default_metadata_getter()]] is used if neither
    is defined.
  * The `getter` to get the field value (defined as a parameter to the field,
    or otherwise constructed automtically from the field name or the specified
    *key* argument).

  The `metadata_getter` must be a function with the signature
  `(locator: Locator, handled_keys: Set[str]) -> Optional[Any]`.

  The `getter` must be a function with the signature
  `(metadata: Any) -> Union[Any, NotSet]`.
  """

  def __init__(self, datatype, default=None, name=None, key=None,
               metadata_getter=None, getter=None):
    super(MetadataField, self).__init__(
      datatype=datatype, nullable=True, required=False,
      default=default, name=name)
    self.derived = True
    self.key = key
    self.metadata_getter = metadata_getter
    self.getter = getter

  @override
  def extract_kwargs(self, object_cls, locator, kwargs, handled_keys):
    assert self.name not in kwargs, (self, object_cls, locator)

    metadata_getter = self.metadata_getter
    if metadata_getter is None:
      metadata_getter = locator.options.get('metadata_getter', None)
    if metadata_getter is None:
      metadata_getter = self.default_metadata_getter

    getter = self.getter
    if getter is None:
      def getter(metadata):
        return metadata.get(self.key or self.name, NotSet)

    metadata = metadata_getter(locator, handled_keys)
    if metadata is not None:
      value = getter(metadata)
      if value is not NotSet:
        kwargs[self.name] = value

  @staticmethod
  def default_metadata_getter(locator, handled_keys):
    value = getattr(locator.value(), '__metadata__', None)
    if not isinstance(value, Mapping):
      value = None
    return value


class FieldSpec(object):
  """
  A container for [[IFieldDescriptor]]s which is used to contain all the
  fields for an [[Object]] subclass.
  """

  classdef.hashable_on('_FieldSpec__fields')

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
      fields.append(field)
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
      fields.append(value)
    return cls(fields)

  @classmethod
  def from_list_def(cls, list_def):
    """
    Compiles a FieldSpec from a list of tuples. Every tuple must have at
    least two elements, the first defining the name of the field, the second
    the type. An optional third field in the tuple may be used to specify
    the field default value.
    """

    fields = []
    for item in list_def:
      if isinstance(item, str):
        field = Field(object, name=item)
      elif isinstance(item, tuple):
        name, datatype = item[:2]
        default = item[2] if len(item) > 2 else NotSet
        field = Field(datatype, default=default, name=name)
        fields.append(field)
      elif IFieldDescriptor.provided_by(item):
        if not item.name:
          raise ValueError('unbound field in __fields__ list')
        field = item
      else:
        raise TypeError('expected {str, tuple, IFieldDescriptor}, got {!r}'
                        .format(type(item).__name__))
      fields.append(field)
    return cls(fields)

  def __init__(self, fields=None):
    """
    Creates a new [[FieldSpec]] object from a list of [[IFieldDescriptor]]
    objects. Note that all fields must have a name, otherwise a [[ValueError]]
    is raised.
    """

    fields = list(fields or [])
    for field in fields:
      if not IFieldDescriptor.provided_by(field):
        raise TypeError('expected IFieldDescriptor, got {!r}'
                        .format(type(field).__name__))
      if not field.name:
        raise ValueError('found unnamed field: {!r}'.format(field))
      assert isinstance(field.name, str), field

    fields.sort(key=lambda x: x.instance_index)

    self.__fields = OrderedDict((x.name, x) for x in fields)
    self.__fields_indexable = fields

  def __getitem__(self, name):
    return self.__fields[name]

  def __contains__(self, name):
    return name in self.__fields

  def __iter__(self):
    return six.iterkeys(self.__fields)

  def __len__(self):
    return len(self.__fields)

  def __repr__(self):
    return 'FieldSpec({!r})'.format(list(self.__fields.values()))

  def keys(self):  # type: () - >Stream[str]
    return Stream(six.iterkeys(self.__fields))

  def values(self):  # type: () -> Stream[Field]
    return Stream(six.itervalues(self.__fields))

  def items(self):  # type: () -> Stream[Tuple[str, Field]]
    return Stream(six.iteritems(self.__fields))

  def update(self, fields):
    # type: (FieldSpec) -> FieldSpec
    """
    Updates this [[FieldSpec]] with the files from another spec and returns
    *self*.

    This operation maintains the order of existing fields in the spec.
    """

    if not isinstance(fields, FieldSpec):
      fields = FieldSpec(fields)

    for key, value in fields.__fields.items():
      self.__fields[key] = value
    self.__fields_indexable = list(self.__fields.values())

    return self

  def get(self, key, default=None):
    return self.__fields.get(key, default)

  def get_index(self, index):
    # type: (int) -> IFieldDescriptor
    return self.__fields_indexable[index]


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
        parent_fields.update(base.__fields__)

    # If there are any class member annotations, we derive the object fields
    # from these rather than from class level [[Field]] objects.
    if hasattr(self, '__fields__') and not isinstance(self.__fields__, FieldSpec):
      fields = FieldSpec.from_list_def(self.__fields__)
    elif hasattr(self, '__annotations__'):
      if isinstance(self.__annotations__, dict):
        fields = FieldSpec.from_annotations(self)
      else:
        fields = FieldSpec.from_list_def(self.__annotations__)
    else:
      fields = FieldSpec.from_class_members(self)

    # Give new fields (non-inherited ones) a chance to propagate their
    # name (eg. to datatypes, this is mainly used to automatically generate
    # a proper class name for inline-declared objects).
    for field in fields.values():
      field.datatype.message(MSG_PROPAGATE_FIELDNAME, self.__name__ + '.' + field.name)

    fields = parent_fields.update(fields)
    for key in fields:
      if key in vars(self):
        delattr(self, key)
    self.__fields__ = fields

    if not hasattr(self, 'Meta'):
      class Meta:
        pass
      self.Meta = Meta

  def __getattr__(self, name):
    field = self.__fields__.get(name)
    if field is not None:
      value = field.get_class_member_value(self)
      if value is not NotSet:
        return value
    raise AttributeError(name)


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
    for field in self.__fields__.values().sortby('priority'):
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
    if type(other) != type(self):
      return True
    for key in self.__fields__:
      if getattr(self, key) == getattr(other, key):
        return False
    return True

  def __repr__(self):
    repr_fields = getattr(self.Meta, META.REPR_FIELDS, self.__fields__)
    attrs = ['{}={!r}'.format(k, getattr(self, k)) for k in repr_fields]
    return '{}({})'.format(type(self).__name__, ', '.join(attrs))

  @classmethod
  def extract(cls, value, locator=None, **options):
    from nr.types.structured import extract
    return extract(value, cls, locator, **options)

  def store(self, locator=None, **options):
    from nr.types.structured import store
    return store(self, type(self), locator, **options)



def create_object_class(name, fields, base=None, mixins=()):
  """
  Creates a new [[Object]] subclass with the specified fields. The fields must
  be a dictionary of bound [[Field]] objects or a dictionary of unbound ones.
  """

  if not isinstance(fields, Mapping):
    assert all(field.name is not None for field in fields), fields
    fields = {field.name: field for field in fields}

  if base is None:
    base = Object

  for key, value in six.iteritems(fields):
    if not isinstance(key, str):
      raise TypeError('class member name must be str, got {}'
                      .format(type(key).__name__))

  return type(name, (base,) + mixins, fields)


__all__ = [
  'IFieldDescriptor',
  'ObjectKeyField',
  'WildcardField',
  'Field',
  'MetadataField',
  'FieldSpec',
  'Object',
  'create_object_class'
]
