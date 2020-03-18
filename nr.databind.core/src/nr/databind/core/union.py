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

""" This module provides a configurable [[UnionType]] for struct fields. """

import importlib
import six
import typing

from nr.collections import abc
from nr.pylang.utils import classdef
from nr.pylang.utils.typing import is_generic, get_generic_args
from nr.interface import attr, default, implements, Interface

from nr.databind.core import IDataType, InvalidTypeDefinitionError
from nr.databind.core.datatypes import PythonClassType, translate_type_def
from nr.databind.core.struct import Struct, StructType

__all__ = [
  'IUnionTypeMember',
  'IUnionTypeResolver',
  'StandardTypeResolver',
  'EntrypointTypeResolver',
  'UnionType'
]


class UnknownUnionTypeError(Exception):
  pass


class IUnionTypeMember(Interface):
  """ Represents a member of a [[UnionType]] as returned by a
  [[IUnionTypeResolver]] when given a type name. This interface provides all
  the information about this union member. """

  classdef.comparable(['name', 'type_name', 'datatype'], decorate=default)

  #: The name of the type in the union.
  name = attr()  # type: str

  #: A more easily identifiable name of the type (eg. the full import name
  #: of te type, or an otherwise descriptive name, can be the same as #name).
  type_name = attr()  # type: str

  #: The #IDataType that is used to deserialize this union type member.
  datatype = attr()  # typE: IDataType

  @default
  def isinstance_check(self, value):  # type: (Any) -> bool
    """ Check if *value* is an instance of this union type member. """

    try:
      self.datatype.isinstance_check(value, True, False)
      return True
    except TypeError:
      return False


class IUnionTypeResolver(Interface):
  """ An interface for resolving union types by a name. """

  classdef.comparable([])

  def resolve(self, type_name):  # type: (str) -> IUnionTypeMember
    """ Resolve the *type_name* to a [[IUnionTypeMember]] instance. If the
    *type_name* is unknown, an [[UnknownUnionTypeError]] must be raised. """

  def reverse(self, value):  # type: (Any) -> IUnionTypeMember
    """ Return the [[IUnionTypeResolver]] for the specified *value*, which is
    whatever [[IUnionTypeMember.create_instance()]] returns. Raises
    [[UnknownUnionTypeError]] if the value cannot be reversed. """

  def members(self):  # type: () -> Iterable[IUnionTypeMember]
    """ List up all the members of this resolver. If listing members is not
    supported, a [[NotImplementedError]] must be raised to indicate that. """


@implements(IUnionTypeResolver)
class StandardTypeResolver(object):
  """ This implementation of the [[IUnionTypeResolver]] uses a static mapping
  of type names to [[Struct]] subclasses. It has two forms of initialization:

  1. A (potentially mixed) list of Python type objects, #StructType or
     #PythonClassType objects. In this case the union type name is derived
     from the `__union_type_name__` or `__name__` member (in this order).
  2. A dictionary of union type names mapping to anything that can be
     translated to an #IDataType with #translate_type_def().
  """

  @implements(IUnionTypeMember)
  class _Member(object):
    def __init__(self, name, datatype):
      self.name = name
      self.type_name = datatype.to_human_readable()
      self.datatype = datatype

  classdef.comparable(['types'])

  def __init__(self, types):
    if isinstance(types, abc.Mapping):
      self.types = types
    elif isinstance(types, (list, tuple)):
      self.types = {}
      for item in types:
        if isinstance(item, StructType):
          item = item.struct_cls
        elif isinstance(item, PythonClassType):
          item = item.cls
        elif isinstance(item, type):
          cls = item
        else:
          raise TypeError('expected StructType, PythonClassType or type '
            'object, got {}'.format(type(item).__name__))
        name = getattr(item, '__union_type_name__', item.__class__)
        self.types[name] = item
    else:
      raise TypeError('expected list/tuple/dict, got {}'
                      .format(type(types).__name__))

    for key, value in self.types.items():
      if not IUnionTypeMember.provided_by(value):
        self.types[key] = self._Member(key, translate_type_def(value))

  def resolve(self, type_name):
    try:
      return self.types[type_name]
    except KeyError:
      raise UnknownUnionTypeError(type_name)

  def reverse(self, value):
    result = None
    for key, member in self.types.items():
      try:
        member.datatype.isinstance_check(value, True, False)
      except TypeError:
        continue
      return member
    raise UnknownUnionTypeError(value)

  def members(self):
    try:
      items = self.types.items()
    except NotImplementedError:
      raise NotImplementedError('wrapped "types" mapping does not support iteration')
    return (x[1] for x in items)


@implements(IUnionTypeResolver)
class EntrypointTypeResolver(StandardTypeResolver):
  """ Collects all entries from an entrypoints group. Checks if the class
  loaded via an entrypoint is either a subclass of the specified *base_type*
  or implements it's interface (if *base_type* is a subclass of [[Interface]]).
  """

  @implements(IUnionTypeMember)
  class _Member(object):
    def __init__(self, name, ep, base_type):
      self.name = name
      self._type_name = None
      self._base_type = base_type
      self._ep = ep
      self._datatype = None
      self._cls_cache = None

    @property
    def _cls(self):
      if self._cls_cache is None:
        cls = self._ep.load()
        if not isinstance(cls, type):
          raise TypeError('expected type object for entrypoint {}, got {}'
            .format(self._ep, type(cls).__name__))
        if self._base_type and not issubclass(cls, self._base_type):
          raise TypeError('expected subclasss of {} for entrypoint {}, got {}'
            .format(self._base_type.__name__, self._ep, cls.__name__))
        self._cls_cache = cls
      return self._cls_cache

    @property
    def type_name(self):
      return self._cls.__name__

    @property
    def datatype(self):
      if self._datatype is None:
        self._datatype = translate_type_def(self._cls)
      return self._datatype

  classdef.comparable(['types', 'base_type'])

  def __init__(self, entrypoint_group, base_type=None):
    import pkg_resources
    types = {}
    for ep in pkg_resources.iter_entry_points(entrypoint_group):
      types[ep.name] = self._Member(ep.name, ep, base_type)
    super(EntrypointTypeResolver, self).__init__(types)
    self.base_type = base_type


@implements(IUnionTypeResolver)
class ImportTypeResolver(object):
  """ This type resolver identifies a union type by their fully qualified
  Python import name, constructed from the `__module__` and `__name__`
  attributes of a type. """

  classdef.comparable([])

  def resolve(self, type_name):  # type: (str) -> IUnionTypeMember
    module_name, member = type_name.rpartition('.')[::2]
    if six.PY2 and module_name == 'builtins':
      module_name = '__builtin__'
    try:
      module = importlib.import_module(module_name)
    except ImportError:
      raise UnknownUnionTypeError(type_name)
    try:
      cls = getattr(module, member)
    except AttributeError:
      raise UnknownUnionTypeError(type_name)
    if not isinstance(cls, type):
      raise UnknownUnionTypeError(type_name)
    try:
      datatype = translate_type_def(cls)
    except InvalidTypeDefinitionError:
      raise UnknownUnionTypeError(type_name)
    return IUnionTypeMember(name=type_name, type_name=type_name,
      datatype=datatype, isinstance_check=lambda x: isinstance(x, cls))

  def reverse(self, value):
    module_name = type(value).__module__
    if six.PY2 and module_name == '__builtin__':
      module_name = 'builtins'
    member = type(value).__name__
    type_name = module_name + '.' + member
    return IUnionTypeMember(
      name=type_name, type_name=type_name,
      datatype=translate_type_def(type(value)),
      isinstance_check=lambda x: isinstance(x, type(value)))

  def members(self):
    raise NotImplementedError


@implements(IDataType)
class UnionType(object):
  """ The UnionType represents multiple types. A value represented by this
  datatype can be of any of the types that are encapsulated by the union
  type. UnionType only supports the encapsulation of [[StructType]]s.

  The UnionType can operate in two modes for the serialization and
  deserialization. In either mode, the object from which the UnionType is
  deserialized must contain a "type" key (configurable with the `type_key`
  parameter).

  In the default mode, the fields for the type are read from the same level.

  ```yaml
  type: onePossibleUnionType
  someField: value
  ```

  With the `nested` option enabled, the values are instead read from an object
  nested with the same name as the type.

  ```yaml
  type: onePossibleUnionType
  onePossibleUnionType:
    someField: value
  ```

  The [[StandardTypeResolver]] is used in the usual case.

  Union type can be conveniently defined using lists with more than one item,
  the [[typing.Union]] type or dictionaries. In case of a dictionary, the
  union type name is defined in the dictionary key. Otherwise, it is read
  from the `__union_type_name__` or classname.
  """

  #: Import these members on the UnionType to reduce the number of
  #: imports that need to be made when implementing a custom type resolver
  #: or creating one of the standard implementations.
  UnknownUnionTypeError = UnknownUnionTypeError
  ITypeMember = IUnionTypeMember
  ITypeResolver = IUnionTypeResolver
  StandardTypeResolver = StandardTypeResolver
  EntrypointTypeResolver = EntrypointTypeResolver
  ImportTypeResolver = ImportTypeResolver

  classdef.comparable(['type_resolver', 'type_key', 'nested'])

  def __init__(self, type_resolver, type_key='type', nested=False):
    # type: (IUnionTypeResolver, str, bool)

    if isinstance(type_resolver, (dict, list, tuple)):
      type_resolver = StandardTypeResolver(type_resolver)

    self.type_resolver = type_resolver
    self.type_key = type_key
    self.nested = nested

  @classmethod
  def from_typedef(cls, recursive, py_type_def):
    if is_generic(py_type_def, typing.Union):
      union_types = get_generic_args(py_type_def)
      if all(issubclass(x, Struct) for x in union_types):
        return UnionType(union_types)
    elif isinstance(py_type_def, list) and len(py_type_def) > 1:
      return UnionType([recursive(x) for x in py_type_def])
    raise InvalidTypeDefinitionError(py_type_def)

  def isinstance_check(self, py_value, strict, coerce):
    try:
      members = list(self.type_resolver.members())
    except NotImplementedError:
      # TODO (@NiklasRosenstein): We use check_value() to type check when
      #   initializing a Struct instance's field, and we don't want that to
      #   fail just because the type resolver doesn't support member listing.
      #   Maybe make this behavior configurable?
      return py_value
    if not any(x.isinstance_check(py_value) for x in members):
      raise TypeError('expected {{{}}}, got {}'.format(
        '|'.join(sorted(x.name for x in members)),
        type(py_value).__name__))
    return py_value

  @classmethod
  def with_entrypoint_resolver(cls, *args, **kwargs):
    """ Returns a #UnionType instance initialized with an
    #EntrypointTypeResolver from the specified *args* and *kwargs*. The
    *type_key* and *nested* keyword arguments are redirected to the
    #UnionType constructor. """

    union_kwargs = {
      k: kwargs.pop(k) for k in ('type_key', 'nested') if k in kwargs}
    return cls(EntrypointTypeResolver(*args, **kwargs), **union_kwargs)

  @classmethod
  def with_import_resolver(cls, *args, **kwargs):
    """ Returns a #UnionType instance initialized with an #ImportTypeResolver
    from the specified *args* and *kwargs*. The *type_key* and *nested*
    keyword arguments are redirected to the #UnionType constructor. """

    union_kwargs = {
      k: kwargs.pop(k) for k in ('type_key', 'nested') if k in kwargs}
    return cls(ImportTypeResolver(*args, **kwargs), **union_kwargs)
