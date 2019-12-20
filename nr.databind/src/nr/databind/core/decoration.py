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

from nr.commons.py import funcdef
import sys

__all__ = ['Decoration', 'ClassDecoration', 'MetadataDecoration', 'TrackLocation']


class Decoration(object):
  """ A decoration is an object that adds behavior to a class or field.
  Specific decorations may be used to decorate functions that serve special
  purposes for the deserializer/serializer or to add properties to a struct
  field. """

  @classmethod
  def all(cls, *values):
    """ Yields all items in the iterable *values* that are instances of the
    decoration. """

    for value in values:
      try_next = ()
      if isinstance(value, type):
        try_next = value.__bases__
      if hasattr(value, '__decorations__'):
        value = value.__decorations__
      elif hasattr(value, 'decorations'):
        value = value.decorations()
      if not isinstance(value, type) and hasattr(value, '__iter__'):
        for item in value:
          if isinstance(item, cls):
            yield item
      for x in cls.all(*try_next):
        yield x

  @classmethod
  def first(cls, *values, **kwargs):
    """ Returns the first value from the iterable *values* that is an instance
    of the decoration. If there is no such value, *fallback* is returned
    instead.

    Parameters:
      *values:
      fallback: A fallback value. Defaults to None. """

    fallback = kwargs.pop('fallback', None)
    funcdef.raise_kwargs(kwargs)
    return next(cls.all(*values), fallback)


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
    return self.__populate__()

  def __populate__(self):
    return self

  @classmethod
  def create(cls, *args, **kwargs):
    self = object.__new__(cls)
    self.__init__(*args, **kwargs)
    return self


class MetadataDecoration(Decoration):

  def enrich_metadata(self, metadata):  # type: (dict)
    raise NotImplementedError

  @classmethod
  def enrich_all(cls, metadata, context, location, *decorations):
    # type: (dict, Union[IDeserializeContext, ISerializeContext], Location, Tuple[Decoration])
    for decoration in cls.all(context, *decorations):
      decoration.enrich_metadata(metadata, context, location)


class TrackLocation(MetadataDecoration, ClassDecoration):

  def enrich_metadata(self, metadata, context, location):
    metadata.location = location
