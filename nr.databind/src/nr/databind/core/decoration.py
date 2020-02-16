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

from nr.pylang.utils import funcdef
import sys


__all__ = [
  'iter_decorations',
  'get_decoration',
  'Decoration',
  'ClassDecoration',
  'DeserializationMetadataDecoration',
  'LocationMetadataDecoration',
  'DeserializeAs',
]


def iter_decorations(of_cls, *decoration_sources):
  # type: (Type[Decoration], Any) -> Iterable[Decoration]
  """ Iterates over all decorations of type *of_cls*. """

  for item in decoration_sources:
    if hasattr(item, 'iter_decorations'):
      it = item.iter_decorations()
    elif hasattr(item, '__decorations__'):
      it = iter(item.__decorations__)
    elif hasattr(item, 'decorations') and hasattr(item.decorations, '__iter__'):
      it = iter(item.decorations)
    elif not isinstance(item, type) and hasattr(item, '__iter__'):
      it = iter(item)
    else:
      # Object does not provide decorations.
      continue
    for sub_item in it:
      if of_cls is None or isinstance(sub_item, of_cls):
        yield sub_item


def get_decoration(of_cls, *decoration_sources, **kwargs):
  # type: (Type[Decoration], Any) -> Optional[Decoration]
  """ Returns the first decoration of the specified type from *items*.
  The keyword-only argument "default" may be specified to control the
  return value that is returned if no matching decoration was found. """

  default = kwargs.pop('default', None)
  funcdef.raise_kwargs(kwargs)
  return next(iter_decorations(of_cls, *decoration_sources), default)


def collect_metadata(metadata, context, location, *decoration_sources):
  # type: (dict, IDeserializeContext, Location, Any) -> None
  """ Finds all #DeserializationMetadataDecoration#s in the
  *decoration_sources* and enriches the *metadata* object using those
  decorations. """

  decorations = iter_decorations(DeserializationMetadataDecoration,
                                 *decoration_sources)
  for item in decorations:
    item.enrich_object_metadata(metadata, context, location)


class Decoration(object):
  """ A decoration is an object that provides additional metadata during
  serialization and deserialization of an object. Decorations can be attached
  to #Struct and #Collection classes, as well as struct fields and the
  serialization or deserialization context. """


class ClassDecoration(Decoration):
  """ A decoration that subclasses this class is automatically added to the
  list of `__decorations__` of the calling frame. If the variable does not
  already exist in the frame, it is initialized with an empty list.

  This is especially useful from a class body to add decorations without
  manually adding them to the `__decorations__` list.

  ```python
  class MyClass(Struct):
    MyClassDecoration()
    assert isinstance(__decorations__[0], MyClassDecoration)
  ```

  It can also be used to decorate functions. In this case, the #__populate__()
  method is usually overriden as it returns the value that is retunred by the
  decoration. In the below example, the `MyDecoration.__populate__()` method
  returns the decorated function.

  ```python
  class MyClass(Struct):
    @MyDecoration
    def my_func(self):
      pass
    assert isinstance(__decorations__[0], MyDecoration)
    assert inspect.isfunction(my_func)
  ```
  """

  def __new__(cls, *args, **kwargs):
    self = object.__new__(cls)
    self.__init__(*args, **kwargs)
    frame = sys._getframe(1)
    try:
      frame.f_locals.setdefault('__decorations__', []).append(self)
    finally:
      del frame
    return self.__populate__()

  def __populate__(self):
    return self


class DeserializationMetadataDecoration(Decoration):
  """ This is the base class for decorations that produce metadata during
  the deserialization of a #Struct or #Collection which is then added to
  the `.__databind__` property of the object.

  An example implementation is the #LocationMetadataDecoration which simply
  adds a `location` field to the metadata dictionary that can later be used
  to trace the origin of the object from the deserialization. """

  def enrich_object_metadata(self, metadata, context, location):
    # type: (dict, IDeserializeContext, Location) -> None
    """ Called to enrich the *metadata* for a #Struct or #Collection during
    its deserialization. If multiple metadata decorations are used, they need
    to be careful not to produce clashing entries in the *metadata* dict. """

    raise NotImplementedError


class LocationMetadataDecoration(DeserializationMetadataDecoration, ClassDecoration):
  """ A metadata decoration that adds a "location" key to the metadata. """

  def enrich_object_metadata(self, metadata, context, location):
    metadata["location"] = location


class DeserializeAs(ClassDecoration):
  """ A class decoration to specify as what type it should be deserialized as.
  This decoration is only consulted for classes that would be represented as a
  #PythonClassType datatype. """

  def __init__(self, datatype):  # type: (IDataType)
    self.datatype = datatype

  def __repr__(self):
    return 'DeserializeAs({!r})'.format(self.datatype)
