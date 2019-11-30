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

import sys


class Decoration(object):
  """ A decoration is an object that adds behavior to a class or field.
  Specific decorations may be used to decorate functions that serve special
  purposes for the deserializer/serializer or to add properties to a struct
  field. """

  @classmethod
  def all(cls, values):
    """ Yields all items in the iterable *values* that are instances of the
    decoration. """

    for value in values:
      if isinstance(value, cls):
        yield value

  @classmethod
  def first(cls, values, fallback=None):
    """ Returns the first value from the iterable *values* that is an instance
    of the decoration. If there is no such value, *fallback* is returned
    instead."""

    return next(cls.all(values), fallback)


class ClassmethodDecoration(Decoration, classmethod):
  """ A #decoration that is intended for decorating a method on a class. """

  def __call__(self, *args, **kwargs):
    return self.__func__(*args, **kwargs)

  @classmethod
  def find_in_class(cls, search_cls):
    """ Searches for an instance of *cls* in the attributes of *search_cls*.
    """

    return cls.first(vars(search_cls).values())


class ClassDecoration(Decoration):
  """ A decoration for a class that can be added by simply calling it from
  within the class definition. Example:

  ```python
  class MyClass(Struct):
    MyClassDecoration()
  ```

  The decoration will be added to the `__decorations__` list of the calling
  scope. If you need to create an instance of this class without also adding
  the instance to the calling scope's `__decorations__` list, use #create().
  """

  def __new__(cls, *args, **kwargs):
    self = cls.create(*args, **kwargs)
    frame = sys._getframe(1)
    try:
      frame.f_locals.setdefault('__decorations__', []).append(self)
    finally:
      del frame

  @classmethod
  def create(cls, *args, **kwargs):
    self = object.__new__(cls)
    self.__init__(*args, **kwargs)
    return self
