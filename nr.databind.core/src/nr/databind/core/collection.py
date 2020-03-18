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

from nr.databind.core.datatypes import CollectionType, translate_type_def
import six


class _CollectionMeta(type):

  def __new__(cls, name, bases, attrs):
    item_type = attrs.get('item_type', object)
    attrs['item_type'] = translate_type_def(item_type)
    return super(_CollectionMeta, cls).__new__(cls, name, bases, attrs)

  @property
  def datatype(cls):  # type: () -> IDataType
    return CollectionType(cls.item_type, cls)


class Collection(six.with_metaclass(_CollectionMeta)):
  """
  Base class for defining a custom collection of items. Using this class
  allows you to define an array/list datatype while adding any attributes or
  methods to it.

  Subclassing [[Collection]] must always be combined with an actual collection
  implementation ([[list]], [[set]], [[collections.deque]], etc.)

  Example:

  ```py
  from nr.databind import Collection, ObjectMapper
  from nr.databind.json import JsonModule

  class Items(list, Collection):
    item_type = str

    def getstring(self):
      return ''.join(self)

  items = ObjectMapper(JsonModue()).deserialize(['a', 'b', 'c'], Items)
  assert items.getstring() == 'abc'
  ```
  """

  def __init__(self, *args, **kwargs):
    super(Collection, self).__init__(*args, **kwargs)
    self.__databind__ = {}
