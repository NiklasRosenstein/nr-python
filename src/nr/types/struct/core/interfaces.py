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

import string

from nr.types.interface import Interface, attr, default
from nr.types.utils import classdef
from .errors import InvalidTypeDefinitionError

try:
  from inspect import getfullargspec as getargspec
except ImportError:
  from inspect import getargspec


class Path(object):
  """
  Represents a chain of location identifiers.
  """

  ROOT_ELEMENT = '$'
  ALLOWED_KEY_CHARS = string.ascii_letters + string.digits + '_-'

  def __init__(self, items):
    self.items = tuple(items)

  def __iter__(self):
    return iter(self.items)

  def __len__(self):
    return len(self.items)

  def __getitem__(self, index):
    return self.items[index]

  def __str__(self):
    """
    Constructs a dotted representation of a path.
    """

    def generate():
      yield Path.ROOT_ELEMENT
      for key in self.items:
        if isinstance(key, int):
          yield '[{}]'.format(key)
        else:
          escaped_key = str(key)
          if '"' in escaped_key:
            escaped_key = escaped_key.replace('"', '\\"')
          if any(c not in Path.ALLOWED_KEY_CHARS for c in escaped_key):
            escaped_key = '"' + escaped_key + '"'
          yield '.' + escaped_key

    return ''.join(generate())

  def to_location(self, value, datatype):
    """
    Creates a new chain of [[Location]] objects of this path. All locations
    except for the final one contain no value or datatype.
    """

    parent = None
    for item in self.items[:-1]:
      parent = Location(parent, item, None, None)
    return Location(parent, self.items[-1] if self.items else None, value, datatype)

  def resolve(self, value): # type: (Union[List, Dict]) -> Any
    """
    Returns the value at this path by subsequently accessing every item in
    the path in *value* and its child nested structures.

    Example:

    ```py
    path = Path(['a', 1, 'foo'])
    data = {'a': [{'foo': 1}, {'foo': 2}]}
    assert path.resolve(data) == 2
    ```
    """

    for item in self.items:
      try:
        value = value[item]
      except KeyError as exc:
        raise KeyError(str(self))
      except IndexError as exc:
        raise IndexError('{} at {}'.format(exc, self))
    return value


class Location(object):
  """
  Represents a location in a nested data structure. It's basically a tuple
  of a parent location, an identifier, a value and a [[IDataType]]. Locations
  are constructed for recursive serialization/deserialization in [[IConverter]]
  implementations.

  An identifier can be a string or integer.
  """

  def __init__(self, parent, ident, value, datatype, options=None):
    # type: (Location, Optional[str], Any, Optional[IDataType])
    if parent and not isinstance(parent, Location):
      raise TypeError('expected Location for argument parent, got {}'.format(
        type(parent).__name__))

    if ident is None:
      if parent is not None:
        raise RuntimeError('Location.ident can only be none without parent')

    if options is None:
      options = parent.options if parent else {}

    self.parent = parent
    self.ident = ident
    self.value = value
    self.datatype = datatype
    self.options = options
    self._path = None

  def __repr__(self):
    return '<Location at {} of {}>'.format(self.path, self.datatype)

  @property
  def path(self):  # type: () -> Path
    if self._path is not None:
      return self._path
    def generator(location):
      while location:
        if location.is_root:
          break
        yield location.ident
        location = location.parent
    self._path = Path(reversed(tuple(generator(self))))
    return self._path

  @property
  def is_root(self):
    return self.ident is None and self.parent is None

  def sub(self, ident, value, datatype):
    return Location(self, ident, value, datatype)


class IDataType(Interface):
  """
  Interface for datatypes. A datatype usually has a one to one mapping with
  a Python type. The serialization/deserialization of the type to other realms
  is handled by the [[IConverter]] interface.

  Datatypes must be comparable. The default string representation is derived
  from the constructor arguments. Datatypes may also provide a more easily
  readable representation with [[to_human_readable()]].
  """

  classdef.comparable([])  # adds __hash__, __eq__, __ne__ to the interface

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
  def to_human_readable(self):  # type: () -> str
    return repr(self)

  @default
  def propagate_field_name(self, name):  # type: (str) -> None
    """
    This method is called when the datatype instance is attached to a field
    in an object. The name of the field is passed to this method. This is
    used for the inline object definition.
    """

  def check_value(self, py_value):  # type: (Any) -> Any
    """
    This method returns *py_value*, or an adaptation of *py_value*, if it
    matches the datatype. If it doesn't, a [[TypeError]] with the reason is
    raised.

    raises TypeError: If the *py_value* doesn't match this datatype.
    """


class ITypeMapper(Interface):
  """
  The type mapper is an interface for an object that controls the adaptation
  of Python type definitions to [[IDataType]]s. This is usually implemented
  as a collection of [[ITypeDefAdapter]] objects.
  """

  def adapt(self, py_type_def):  # type: (Any) -> IDataType
    # raises: InvalidTypeDefinitionError
    pass


class ITypeDefAdapter(Interface):
  """
  Adapts a Python type definition to an [[IDataType]].
  """

  priority = attr(int, default=0)

  def adapt(self, mapper, py_type_def):  # type: (ITypeMapper, Any) -> IDataType
    """
    raises InvalidTypeDefinitionError: If the object is unable to adapt the
      *py_type_def* to an [[IDataType]].
    """

  @default
  def __repr__(self):
    return type(self).__name__


class IObjectMapper(Interface):
  """
  The object mapper controls how values and their associated data types are
  serialized and deserialized. This is usually implemented as a collection of
  [[IConverter]] instances.
  """

  def deserialize(self, location):  # type: (Location) -> Any
    pass

  def serialize(self, location):  # type: (Location) -> Any
    pass


class IConverter(Interface):
  """
  An interface that simply describes converting Python values of an
  [[IDataType]] to another serialized form, and the reverse.
  """

  priority = attr(int, default=0)
  namespace = attr(str, default=None, static=True)

  def accept(self, datatype):  # type: (IDataType) -> Any
    pass

  def deserialize(self, mapper, locator):  # type: (IObjectMapper, Locator) -> Any
    pass

  def serialize(self, mapper, locator):  # type: (IObjectMapper, Locator) -> Any
    pass

  @default
  def __repr__(self):
    return type(self).__name__


__all__ = [
  'Path',
  'Location',
  'IDataType',
  'ITypeMapper',
  'ITypeDefAdapter',
  'IObjectMapper',
  'IConverter'
]
