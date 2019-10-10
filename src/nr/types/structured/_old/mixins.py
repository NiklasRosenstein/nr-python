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
Some mixins for [[Object]] subclasses.
"""

import six
from nr.types import abc


class ToJSON(object):
  """
  Adds the [[#to_json()]] method. This is different from the [[AsDict]] mixin
  in that it is called recursively on any of the attributes if they have a
  `to_json()` method.
  """

  def to_json(self):
    """
    Converts the object to a representation that can be dumped into JSON
    format. For any member, it will check if that member has a `to_json()`
    method and call it. Mappings and sequences are converted recursively.

    Note that this method does not guarantee that the returned object will
    be JSON serializable afterwards. For special cases, the method should
    be overwritten.
    """

    def convert(value):
      if hasattr(value, 'to_json'):
        return value.to_json()
      elif isinstance(value, abc.Mapping):
        return dict((k, value[k]) for k in value)
      elif isinstance(value, abc.Sequence) and not isinstance(value, (six.string_types, six.binary_type, bytearray)):
        return [convert(x) for x in value]
      else:
        return value

    result = {}
    for key in self.__fields__:
      result[key] = convert(getattr(self, key))
    return result


class AsDict(object):
  """
  Adds an [[#as_dict()]] method.
  """

  def as_dict(self):
    return dict((k, getattr(self, k)) for k in self.__fields__)


class Sequence(object):
  """
  Adds the mutable sequence interface to an object.
  """

  def __iter__(self):
    for key in self.__fields__:
      yield getattr(self, key)

  def __len__(self):
    return len(self.__fields__)

  def __getitem__(self, index):
    if hasattr(index, '__index__'):
      return getattr(self, self.__fields__.get_index(index.__index__()).name)
    elif isinstance(index, str):
      return getattr(self, str)
    else:
      raise TypeError('cannot index with {} object'
                      .format(type(index).__name__))

  def __setitem__(self, index, value):
    if hasattr(index, '__index__'):
      setattr(self, self.__fields__[index.__index__()].name, value)
    elif isinstance(index, str):
      setattr(self, index, value)
    else:
      raise TypeError('cannot index with {} object'
                      .format(type(index).__name__))


__all__ = ['ToJSON', 'AsDict', 'Sequence']
