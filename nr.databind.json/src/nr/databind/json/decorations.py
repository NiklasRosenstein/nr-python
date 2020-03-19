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

from nr.databind.core import decorations as _d, IDeserializer, ISerializer
from nr.interface import implements
from nr.pylang.utils import classdef


### Helper classes
##################

@implements(IDeserializer, ISerializer)
class _Wrapper(object):

  def __init__(self, func):
    self._func = func

  def deserialize(self, mapper, node):
    try:
      return self._func(mapper, node)
    except ValueError as e:
      raise node.value_error(e)
    except TypeError as e:
      raise node.type_error(e)

  serialize = deserialize


class JsonFieldName(_d.FieldName):
  pass


class JsonDefault(_d.FieldDecoration):
  """
  A decoration that overrides the default value of a field when it is
  deserialized from JSON. The value specified here is deserialized in place.
  """

  def __init__(self, value):
    self.value = value

  def __repr__(self):
    return 'JsonDecoration(value={!r})'.format(self.value)


class JsonSerializer(_d.ClassDecoration, _d.FieldDecoration):
  """
  A decoration that allows to override the (de-) serializer for a class or
  field. The *serializer* may be an #IDeserializer or an #ISerializer, or
  both.

  Alternatively, function objects or method names can be specified for that
  will be used during the (de-) serialization instead.
  """

  classdef.repr(['impl', 'serialize', 'deserialize'])

  def __init__(self, impl=None, serialize=None, deserialize=None):
    if impl is not None and not IDeserializer.provided_by(impl) \
        and not ISerializer.provided_by(impl):
      raise TypeError('impl must be None or IDeserializer or ISerializer, got "{}"'
                      .format(type(impl).__name__))
    if serialize is not None and not isinstance(serialize, str) and not callable(serializer):
      raise TypeError('serialize must be None, str or callable, got "{}"'
                      .format(type(serialize).__name__))
    if deserialize is not None and not isinstance(deserialize, str) and not callable(deserializer):
      raise TypeError('deserialize must be None, str or callable, got "{}"'
                      .format(type(deserialize).__name__))
    self.impl = impl
    self.serialize = serialize
    self.deserialize = deserialize

  @classmethod
  def inheritable(cls):
    return True

  def __get(self, method, cls, interface):  # type: (str, Type, Type) -> Union[IDeserializer, ISerializer]
    if isinstance(method, str):
      return _Wrapper(getattr(cls, method))
    elif callable(method):
      return _Wrapper(method)
    elif self.impl and interface.provided_by(impl):
      return self.impl
    else:
      return None

  def get_deserializer(self, cls):  # type: () -> Optional[IDeserializer]
    return self.__get(self.deserialize, cls, IDeserializer)

  def get_serializer(self, cls):  # type: () -> Optional[IDeserializer]
    return self.__get(self.serialize, cls, ISerializer)


class JsonSerializeCollectionAs(_d.ClassDecoration, _d.FieldDecoration):
  """
  A decoration to configure the Python type that should be used for the
  JSON representation of a collection when serializing.
  """

  def __init__(self, cls):
    self.cls = cls


class JsonSerializeObjectAs(_d.ClassDecoration, _d.FieldDecoration):
  """
  A decoration to configure the Python type that should be used for the
  JSON representation of an object when serializing.
  """

  def __init__(self, cls):
    self.cls = cls
