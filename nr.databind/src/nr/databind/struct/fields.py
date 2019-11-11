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
from nr.singleton import NotSet
from nr.stream import Stream
from nr.types.utils import classdef
from nr.types.utils.typing import extract_optional
from .. import get_type_mapper
from ..core.datatypes import ObjectType, StringType
from ..core.errors import ExtractTypeError, ExtractValueError
from ..core.interfaces import IDataType, Location


class DeserializeDefault(object):
  """ A useful class for [[Field.default]]. """

  def __init__(self, value, mapper):
    self.value = value
    self.mapper = mapper

  def deserialize(self, datatype):
    location = Location(None, 'default', self.value, datatype)
    return self.mapper.deserialize(location)


def with_instance_index(
    attr_name='instance_index',
    counter_name='_INSTANCE_INDEX_COUNTER'):

  def decorator(cls):
    setattr(cls, counter_name, 0)

    wrapped = cls.__init__

    @functools.wraps(wrapped)
    def __init__(self, *args, **kwargs):
      index = getattr(cls, counter_name)
      setattr(self, attr_name, index)
      setattr(cls, counter_name, index + 1)
      return wrapped(self, *args, **kwargs)

    cls.__init__ = __init__
    return cls

  return decorator


@with_instance_index()
class StructField(object):
  """ Base class for struct fields. The *datatype* field will be translated
  to an [[IDatatype]] instance when it is processed by the [[_StructMeta]]
  class. """

  classdef.comparable('__class__ name datatype required')

  def __init__(self, name, datatype, required, nullable=False,
               options=None, mapper=None):
    assert name is None or isinstance(name, str), repr(name)
    if type(self) == StructField:
      raise RuntimeError('StructField cannot be instantiated directly.')
    if not IDataType.provided_by(datatype):
      if not mapper:
        raise RuntimeError('StructField(datatype) = {!r} parameter does not '
                           'implement IDataType and must therefore be '
                           'converted with an ITypeMapper, but no mapper '
                           'was provided.'.format(datatype))
      datatype = mapper.adapt(datatype)
    # type: (Optional[str], Any, bool, Optional[dict])
    self.name = name
    self.datatype = datatype
    self.required = required
    self.nullable = nullable
    self.options = options or {}

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
    """ Sets the name of the field. if the name is already set, a [[RuntimeError]]
    will be raised. """

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
    """ Return the default value for this field. Raises a [[NotImplementedError]]
    if the field does not provide a default value. """

    raise NotImplementedError

  def extract_kwargs(self, mapper, struct_cls, location, kwargs, handled_keys):
    # type: (Type[Struct], location, Dict[str, Any], Set[str]) -> None
    """ This method is called from the [[StructConverter.deserialize()]]
    method to compose the [[Struct]] keyword arguments for construction. """


class ObjectKeyField(StructField):
  """ This is a [[StringType]] field that extracts the key with which the
  object is defined in its parent structure. """

  def __init__(self, name=None, serialize=False, nullable=False,
               required=True, options=None):
    super(ObjectKeyField, self).__init__(
      name, StringType(), required, nullable, options)
    self.serialize = serialize

  def is_derived(self):
    return not self.serialize

  def get_default_value(self):
    raise NotImplementedError

  def extract_kwargs(self, mapper, struct_cls, location, kwargs, handled_keys):
    if self.serialize and self.name in location.value:
      handled_keys.add(self.name)
      kwargs[self.name] = location.value[self.name]
    else:
      assert self.name not in kwargs, (self, object_cls, location)
      kwargs[self.name] = location.ident


class WildcardField(StructField):
  """ This field consumes all extranous fields in a nested structure when an
  object is extracted and puts them into a map. """

  REPORT = 'report'  #: default
  IGNORE = 'ignore'
  IGNORE_AND_CONSUME = 'ignore_consume'

  def __init__(self, value_type, nullable=False, options=None, name=None,
               mapper=None, invalid_keys=REPORT):
    mapper = mapper or get_type_mapper(_stackdepth=1)
    value_type = mapper.adapt(value_type)
    super(WildcardField, self).__init__(name,
      ObjectType(value_type), False, nullable, options, mapper)
    self.value_type = value_type
    self.invalid_keys = invalid_keys

  def is_derived(self):
    return False

  def get_default_value(self):
    return {}

  def extract_kwargs(self, mapper, struct_cls, location, kwargs, handled_keys):
    assert self.name not in kwargs, (self, struct_cls, location)
    result = {}
    for key, value in six.iteritems(location.value):
      if key in handled_keys:
        continue
      try:
        sub_location = location.sub(key, value, self.value_type)
        value = mapper.deserialize(sub_location)
        result[key] = value
      except ExtractTypeError:
        if self.invalid_keys == self.IGNORE:
          pass
        elif self.invalid_keys == self.IGNORE_AND_CONSUME:
          handled_keys.add(key)
        else:
          raise
    handled_keys.update(result)
    kwargs[self.name] = result


class Field(StructField):
  """ This is the standard field. """

  def __init__(self, datatype, nullable=False, required=None,
               default=NotSet, name=None, options=None, mapper=None):
    if default is None:
      nullable = True
    if required is None:
      if default is NotSet:
        required = True
      else:
        required = False
    if not IDataType.provided_by(datatype):
      datatype = (mapper or get_type_mapper(_stackdepth=1)).adapt(datatype)
    super(Field, self).__init__(name, datatype, required, nullable, options)
    self.default = default

  def __repr__(self):
    return 'Field(datatype={!r}, nullable={!r}, default={!r}, name={!r})'\
      .format(self.datatype, self.nullable, self.default, self.name)

  def get_default_value(self):
    if self.default is NotSet:
      raise RuntimeError('Field({!r}).default is NotSet'.format(self.name))
    if isinstance(self.default, DeserializeDefault):
      return self.default.deserialize(self.datatype)
    if callable(self.default):
      return self.default()
    return self.default

  def extract_kwargs(self, mapper, struct_cls, location, kwargs, handled_keys):
    assert self.name not in kwargs, (self, struct_cls, location)
    key = self.options.get('json_key', self.name)
    if key not in location.value:
      if self.required:
        raise ExtractValueError(location, "missing member \"{}\" for {} object"
                                .format(key, struct_cls.__name__))
      return
    value = location.value[key]
    if self.nullable and value is None:
      kwargs[self.name] = None
    else:
      sub_location = location.sub(key, value, self.datatype)
      kwargs[self.name] = mapper.deserialize(sub_location)
    handled_keys.add(key)


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
  `(location: Location, handled_keys: Set[str]) -> Optional[Any]`.

  The `getter` must be a function with the signature
  `(metadata: Any) -> Union[Any, NotSet]`.
  """

  def __init__(self, datatype, default=None, name=None, key=None,
               metadata_getter=None, getter=None, mapper=None):
    super(MetadataField, self).__init__(
      datatype=datatype, nullable=True, required=False,
      default=default, name=name, mapper=mapper or get_type_mapper(_stackdepth=1))
    self.key = key
    self.metadata_getter = metadata_getter
    self.getter = getter

  def is_derived(self):
    return True

  def extract_kwargs(self, mapper, struct_cls, location, kwargs, handled_keys):
    assert self.name not in kwargs, (self, struct_cls, location)

    metadata_getter = self.metadata_getter
    if metadata_getter is None:
      metadata_getter = mapper.get_option('metadata_getter', None)
    if metadata_getter is None:
      metadata_getter = self.default_metadata_getter

    getter = self.getter
    if getter is None:
      def getter(metadata):
        return metadata.get(self.key or self.name, NotSet)

    metadata = metadata_getter(location, handled_keys)
    if metadata is not None:
      value = getter(metadata)
      if value is not NotSet:
        kwargs[self.name] = value

  @staticmethod
  def default_metadata_getter(location, handled_keys):
    value = getattr(location.value, '__metadata__', None)
    if not isinstance(value, abc.Mapping):
      value = None
    return value


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
  def from_dict(cls, fields_dict, mapper=None):
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
  def from_annotations(cls, obj_class, mapper=None):
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
        name=name,
        mapper=mapper)
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
  def from_list_def(cls, list_def, mapper=None):
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
        field = Field(datatype, default=default, name=name, mapper=mapper)
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
  'DeserializeDefault',
  'StructField',
  'ObjectKeyField',
  'WildcardField',
  'Field',
  'MetadataField',
  'FieldSpec',
]
