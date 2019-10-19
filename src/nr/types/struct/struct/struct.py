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

from nr.types import abc
from .. import get_type_mapper
from ..core.datatypes import CollectionType
from .fields import FieldSpec


class _StructMeta(type):
  """ Private. Meta class for the [[Struct]] class. Handles the following
  things for [[Struct]] subclasses:

    * Processes the field declarations and sets `__fields__`
    * Ensures `Meta` exists on the subclass
  """

  def __init__(self, name, bases, attrs):
    mapper = attrs.get('__type_mapper__', None)
    mapper = mapper or get_type_mapper(attrs.get('__module__'))

    # Collect inherited fields.
    parent_fields = FieldSpec()
    for base in bases:
      if hasattr(base, '__fields__') and isinstance(base.__fields__, FieldSpec):
        parent_fields.update(base.__fields__)

    # If there are any class member annotations, we derive the object fields
    # from these rather than from class level [[Field]] objects.
    if hasattr(self, '__fields__') and not isinstance(self.__fields__, FieldSpec):
      fields = FieldSpec.from_list_def(self.__fields__, mapper)
    elif hasattr(self, '__annotations__'):
      if isinstance(self.__annotations__, dict):
        fields = FieldSpec.from_annotations(self, mapper)
      else:
        fields = FieldSpec.from_list_def(self.__annotations__, mapper)
    else:
      fields = FieldSpec.from_class_members(self)
      if not fields and hasattr(self, '__fields__'):
        fields = self.__fields__

    # Give new fields (non-inherited ones) a chance to propagate their
    # name (eg. to datatypes, this is mainly used to automatically generate
    # a proper class name for inline-declared objects).
    for field in fields.values():
      field.datatype.propagate_field_name(self.__name__ + '.' + field.name)

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


@six.add_metaclass(_StructMeta)
class Struct(object):
  """
  An object is comprised of field descriptors and metadata which are used to
  build the object from a nested structure. Objects can be defined in two
  major ways: With the [[Field]] class, or with the class member annotation
  syntax that is available since Python 3.6.

  With annotations:

  ```py
  from typing import Optional
  class Person(Struct):
    name: str
    age: Optional[int]
    telephone_numbers: [str] = lambda: []
  ```

  With the [[Field]] class:

  ```py
  class Person(Struct):
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
      kwargs[field.name] = field.datatype.check_value(arg)

    # Extract all fields.
    handled_keys = set()
    for field in self.__fields__.values().sortby(lambda x: x.get_priority()):
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
    attrs = ['{}={!r}'.format(k, getattr(self, k)) for k in self.__fields__]
    return '{}({})'.format(type(self).__name__, ', '.join(attrs))


class _CustomCollectionMeta(type):

  def __new__(cls, name, bases, attrs):
    item_type = attrs.get('item_type', object)
    mapper = get_type_mapper(attrs['__module__'])
    attrs['item_type'] = mapper.adapt(item_type)
    return super(_CustomCollectionMeta, cls).__new__(cls, name, bases, attrs)

  @property
  def datatype(cls):  # type: () -> IDataType
    return CollectionType(cls.item_type, cls)


@six.add_metaclass(_CustomCollectionMeta)
class CustomCollection(object):
  """ The base class for defining a custom collection of items. Using this
  class allows you to define an array/list datatype while adding any
  attributes or methods to it.

  Subclassing [[CustomCollection]] must always be combined with an actual
  collection implementation ([[list]], [[set]], [[collections.deque]], etc.)

  Example:

  ```py
  from nr.type.structured import CustomCollection, CollectionType, StringType, deserialize

  class Items(CustomCollection, list):
    item_type = str

    def do_stuff(self):
      return ''.join(self)

  assert Items.datatype == ArrayType(StringType())

  items = extract(['a', 'b', 'c'], Items)
  assert items.do_stuff() == 'abc'
  ```
  """

  __location__ = None


def create_struct_class(name, fields, base=None, mixins=()):
  """
  Creates a new [[Struct]] subclass with the specified fields. The fields must
  be a dictionary of bound [[Field]] objects or a dictionary of unbound ones.
  """

  if not isinstance(fields, abc.Mapping):
    assert all(field.name is not None for field in fields), fields
    fields = {field.name: field for field in fields}

  if base is None:
    base = Struct

  for key, value in six.iteritems(fields):
    if not isinstance(key, str):
      raise TypeError('class member name must be str, got {}'
                      .format(type(key).__name__))

  return type(name, (base,) + mixins, fields)


__all__ = ['Struct', 'CustomCollection', 'create_struct_class']
