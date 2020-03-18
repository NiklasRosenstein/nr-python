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

"""
Provides the #JsonModule class which can be used in an #ObjectMapper to (de-)
serialize data from and to JSON representation.
"""

__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
__version__ = '0.0.1'

from nr.databind.core import *
from nr.databind.json import serializers as _s
from nr.databind.json.decorations import *
import datetime
import json


class JsonModule(Module):
  """
  The JSON module allows the (de-) serialization of values from or to JSON
  representation.
  """

  def __init__(self):
    super(JsonModule, self).__init__()
    self.register(AnyType, _s.AnySerializer())
    self.register(BooleanType, _s.BooleanSerializer())
    self.register(StringType, _s.StringSerializer())
    self.register(IntegerType, _s.IntegerSerializer())
    self.register(DecimalType, _s.DecimalSerializer())
    self.register(CollectionType, _s.CollectionSerializer())
    self.register(ObjectType, _s.ObjectSerializer())
    self.register(StructType, _s.StructSerializer())
    self.register(MultiType, _s.MultiTypeSerializer())
    self.register(UnionType, _s.UnionTypeSerializer())
    self.register(ProxyType, _s.ProxyTypeSerializer())
    self.register(PythonClassType, _s.PythonClassSerializer())

    self.register(datetime.date, _s.DateSerializer())
    self.register(datetime.datetime, _s.DatetimeSerializer())

    try: import enum
    except ImportError: enum = None
    else:
      self.register(
        lambda dt: type(dt) == PythonClassType and issubclass(dt.cls, enum.Enum),
        _s.EnumSerializer())


class JsonMixin(object):
  """
  A mixin for #Struct or #Collection subclasses that adds #to_json() and
  #from_json() methods which de/serialize an instance of the class with an
  #ObjectMapper and the #JsonModule.
  """

  def to_json(self, *args, **kwargs):
    mapper = ObjectMapper(JsonModule())
    return mapper.serialize(self, type(self), *args, **kwargs)

  @classmethod
  def from_json(cls, data, *args, **kwargs):
    mapper = ObjectMapper(JsonModule())
    return mapper.deserialize(data, cls, *args, **kwargs)


class JsonEncoder(json.JSONEncoder):
  """
  A #json.JSONEncoder implementation that supports serializing objects into JSON
  from their Python type via an #ObjectMapper.
  """

  def __init__(self, mapper):
    super(JsonEncoder, self).__init__()
    self._mapper = mapper

  def default(self, obj):
    try:
      datatype = translate_type_def(type(obj))
    except InvalidTypeDefinitionError:
      pass
    else:
      return self._mapper.serialize(obj, datatype)
    return super(JsonEncoder, self).default(obj)
