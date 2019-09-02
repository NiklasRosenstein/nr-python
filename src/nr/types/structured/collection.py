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
from .types import translate_field_type, ArrayType


class _CollectionClass(type):

  def __new__(cls, name, bases, attrs):
    item_type = attrs.get('item_type', object)
    attrs['item_type'] = translate_field_type(item_type)
    return super(_CollectionClass, cls).__new__(cls, name, bases, attrs)

  @property
  def datatype(cls):  # type: () -> IDataType
    return ArrayType(cls.item_type, cls)


@six.add_metaclass(_CollectionClass)
class Collection(object):
  """
  The base class for declaring a collection of items of a specific type. Using
  this class allows you to define an array/list datatype while adding any
  attributes or methods to it.

  Subclassing [[Collection]] must always be combined with an actual collection
  implementation ([[list]], [[set]], [[collections.deque]], etc.)

  Example:

  ```py
  from nr.type.structured import Collection, ArrayType, StringType, extract

  class Items(Collection, list):
    item_type = str

    def do_stuff(self):
      return ''.join(self)

  assert Items.datatype == ArrayType(StringType())

  items = extract(['a', 'b', 'c'], Items)
  assert items.do_stuff() == 'abc'
  ```
  """


__all__ = ['Collection']
