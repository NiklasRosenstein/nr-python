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

from nr.pylang.utils import classdef
from nr.interface import Interface, attr, default
from typing import ContextManager
from .errors import InvalidTypeDefinitionError
from .location import Location

try:
  from inspect import getfullargspec as getargspec
except ImportError:
  from inspect import getargspec


class IDataType(Interface):
  """ Interface for datatypes. A datatype usually has a one to one mapping
  with a Python type. The serialization/deserialization of the type to other
  realms is handled by the #IDeserializer and #ISerializer interfaces.

  Datatypes must be comparable. The default string representation is derived
  from the constructor arguments. Datatypes may also provide a more easily
  readable representation with #to_human_readable().

  A datatype also describes how it can be created from a more Pythonic
  description via the #from_typedef() function.

  To implement an #IDataType, it is recommendable to use
  #classdef.comparable(). """

  classdef.comparable([])  # adds __hash__, __eq__, __ne__ to the interface
  priority = attr(int, default=0, static=True)

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
    """ This method is called when the datatype instance is attached to a
    field in an object. The name of the field is passed to this method. This
    is used for the inline object definition. """

  @classmethod
  def from_typedef(cls, recursive, py_type_def):  # type: (Callable, Any) -> IDataType
    # raises: InvalidTypeDefinitionError
    """ Convert the datatype from a pure Python description. Raise an
    #InvalidTypeDefinitionError if the *py_type_def* cannot be translated to
    this datatype. """

  def check_value(self, py_value):  # type: (Any) -> Any
    """ This method returns *py_value*, or an adaptation of *py_value*, if it
    matches the datatype. If it doesn't, a [[TypeError]] with the reason is
    raised.

    raises TypeError: If the *py_value* doesn't match this datatype. """


class IBaseContext(Interface):

  def iter_decorations(self):  # type: () -> Iterable[Decoration]
    """ Return an iterable of decorations that are set globally. """


class IDeserializeContext(IBaseContext):
  """ Context for deserializing values. """

  def deserialize(self, value, datatype, key=None, filename=None, decorations=None):
    # type: (Any, IDataType, Union[str, Sequence, None], Optional[str], Optional[List[Decoration]])
    pass


class ISerializeContext(IBaseContext):
  """ Context for serializing values. """

  def serialize(self, value, datatype, key=None, filename=None, decorations=None):
    # type: (Any, IDataType, Union[str, Sequence, None], Optional[str], Optional[List[Decoration]])
    pass


class IDeserializer(Interface):
  """ Interface for deserializing values of a given #IDataType. """

  @default
  def __repr__(self):
    return type(self).__name__

  def deserialize(self, context, location):  # type: (IDeserializeContext, Location) -> Any
    pass


class ISerializer(Interface):
  """ Interface for serializing values of a given #IDataType. """

  @default
  def __repr__(self):
    return type(self).__name__

  def serialize(self, context, location):  # type: (ISerializeContext, Location) -> Any
    pass


from .decoration import Decoration


__all__ = [
  'IDataType',
  'IDeserializeContext',
  'ISerializeContext',
  'IDeserializer',
  'ISerializer',
]
