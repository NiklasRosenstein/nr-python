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

from nr.types.singletones import NotSet


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

    return cls

  return decorator


@with_instance_index()
class StructField(Interface):
  """
  Base class for struct fields.
  """

  classdef.comparable('__class__ name datatype required',
                       decorate=default)

  def __init__(self, name, datatype, required):
    # type: (Optional[str], IDataType, bool)
    self.name = name
    self.datatype = datatype
    self.required = required

  def get_priority(self):  # type: () -> int
    """
    The priority determines when the field will have its chance to
    extract values from the source dictionary. The default priority
    is zero (0).
    """

    return 0

  def is_derived(self):  # type: () -> bool
    """
    Returns True if the field is a derived field and thus should be ignored
    when serializing the struct.
    """

    return False

  def set_name(self, name):  # type: str -> None
    """
    Sets the name of the field. if the name is already set, a [[RuntimeError]]
    will be raised.
    """

    if self.name is not None:
      raise RuntimeError('cannot set field name to {!r}, name is already '
                         'set to {!r}'.format(name, self.name))
    if not isinstance(name, str):
      raise TypeError('StructField.name must be a string, got {}'
                      .format(type(name).__name__))
    self.name = name

  def get_struct_class_member(self, object_cls):  # type: (Type[Object]) -> Any
    """
    This method is called when the field is accessed via
    [[StructMeta.__getattr__()]] and can be used to expose a class-level
    property on the [[Struct]] class.

    Return [[NotSet]] if no property is to be exposed.

    The default implementation checks if the [[.datatype]] is an instance of
    [[StructType]] and returns the wrapped [[Struct]] subclass in that case.
    """

    if isinstance(self.datatype, StructType):
      return self.datatype.object_cls
    return NotSet

  def get_default_value(self):  # type: () -> Any
    """
    Return the default value for this field. Raises a [[NotImplementedError]]
    if the field does not provide a default value.
    """

    raise NotImplementedError

  def extract_kwargs(self, object_cls, location, kwargs, handled_keys):
    # type: (Type[Object], location, Dict[str, Any], Set[str]) -> None
    """
    This method is called from the [[StructConverter.deserialize()]] [[StructType.extract()]] method to
    compose the [[Object]] keyword arguments for construction.

    The field must specify the keys from [[Locator.value()]] that were
    treated in this method to prevent an error for an extract key if
    [[META.EXTRACT_STRICT]] is set.
    """


class FieldSpec(object):
  """
  A container for [[StructField]]s which is used to collect all fields of a
  [[Struct]] in a single place.
  """

  classdef.comparable('_fields')

  def __init__(self, fields=None):
    """
    Creates a new [[FieldSpec]] object from a list of [[StructField]]
    objects. Note that all fields must have a name, otherwise a [[ValueError]]
    is raised.
    """

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
    Compiles a [[FieldSpec]] object from the class members that are subclasses
    of [[StructField]].
    """

    fields = []
    for name, value in six.iteritems(vars(obj_class)):
      if not isinstance(value, StructField):
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
    """
    Updates this [[FieldSpec]] with the files from another spec and returns
    *self*.

    This operation maintains the order of existing fields in the spec.
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
