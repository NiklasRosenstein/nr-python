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

import collections
import string
from nr.types.interface import Interface, default, implements, override


def format_location_path(path):
  def generate():
    for key in path:
      if key == Locator.ROOT_ELEMENT:
        yield key
      elif isinstance(key, int):
        yield '[{}]'.format(key)
      else:
        escaped_key = str(key)
        if '"' in escaped_key:
          escaped_key = escaped_key.replace('"', '\\"')
        if any(c not in Locator.ALLOWED_KEY_CHARS for c in escaped_key):
          escaped_key = '"' + escaped_key + '"'
        yield '.' + escaped_key
  return ''.join(generate())


class Locator(object):
  """
  Represents a location in a nested structure with the current value and
  datatype. Usually this is started from a [[Locator.root()]] element.
  [[IDataType.extract()]] and [[IDataType.store()]] will use
  [[Locator.advance()]] when entering extraction/storing recursively.

  A locator can also point to the middle of a nested structure without
  prior traversing of the parent elements using the [[Locator.proxy()]]
  method. A common use case for this is when a structured object should
  only be retrieved starting from a specific location. Example:

  ```py
  locator = Locator.proxy(['config', 'starts', 'here'])
  locator = locator.emplace(locator.resolve(input_data), ObjectType(ConfigObject))
  config = locator.extract()
  ```

  Note that the [[extract()]] function makes this a little shorter:

  ```py
  locator = Locator.proxy(['config', 'starts', 'here'])
  config = extract(locator.resolve(input_data), ConfigObject, locator)
  ```
  """

  ROOT_ELEMENT = '$'
  ALLOWED_KEY_CHARS = string.ascii_letters + string.digits + '_-'

  @classmethod
  def root(cls, value, datatype, options=None):  # type: (Any, Optional[IDataType]) -> Locator
    return cls(None, None, value, datatype, options or {})

  @classmethod
  def proxy(cls, path, end_value=None, end_datatype=None):  # type: List[Union[str, int]] -> Locator
    locator = Locator.root(None, AnyType())
    for key in path:
      locator = locator.advance(key, None, AnyType())
    locator.__value = end_value
    locator.__datatype = end_datatype
    return locator

  def __init__(self, parent, key, value, datatype, options=None):
    # type: (Optional[Locator], Union[str, int], Any, Optional[IDataType]) -> None
    assert parent is not None or key is None, "root element can not have a key"
    self.__parent = parent
    self.__key = key
    self.__value = value
    self.__datatype = datatype
    self.__options = options

  def __str__(self):
    return format_location_path(self.path)

  @property
  def path(self):
    result = [self.ROOT_ELEMENT if not x.__parent else x.__key
              for x in self.iter()]
    result.reverse()
    assert result[0] == self.ROOT_ELEMENT
    return result

  @property
  def path_of_locators(self):
    result = list(self.iter())
    result.reverse()
    assert result[0].is_root()
    return result

  @property
  def options(self):  # type: () -> Dict
    if self.__options is not None:
      return self.__options
    if self.__parent:
      return self.__parent.options
    raise RuntimeError("improper Locator structure, root always has options")

  def is_root(self):
    return self.__parent is None

  def key(self):  # type: () -> Union[None, str, int]
    return self.__key

  def value(self):  # type: () -> Any
    return self.__value

  def datatype(self):  # type: Any -> IDataType
    return self.__datatype

  def parent(self):  # type: () -> Optional[Locator]
    return self.__parent

  def advance(self, key, value, datatype):  # type: () -> Locator
    return Locator(self, key, value, datatype)

  def resolve(self, value): # type: (Union[List, Dict]) -> Any
    """
    Returns the value that this location represents given another root
    structure. This is only really useful in combination with a locator
    created with the [[Locator.proxy()]] function.

    Example:

    ```py
    locator = Locator.proxy(['a', 1, 'foo'])
    data = {'a': [{'foo': 1}, {'foo': 2}]}
    assert locator.resolve(data) == 2
    ```
    """

    for locator in self.path_of_locators[1:]:
      try:
        value = value[locator.__key]
      except KeyError as exc:
        raise KeyError(str(locator))
      except IndexError as exc:
        raise IndexError('{} at {}'.format(exc, locator))
    return value

  def emplace(self, value, datatype, options=None):  # type: (Any, IDataType) -> None
    """
    Creates a new Locator at the same location with a different value and
    datatype. This is usually useful if the locator was created with the
    [[Locator.proxy()]] function if not initial value and datatype was
    specified.
    """

    if options is None:
      options = self.__options
    return Locator(self.__parent, self.__key, value, datatype, options)

  def iter(self):
    current = self
    while current:
      yield current
      current = current.__parent

  def type_error(self, message=None):
    """
    Raises a #ExtractTypeError for this location.
    """

    raise ExtractTypeError(self, message)

  def value_error(self, message):
    """
    Raises a #ExtractValueError for this location.
    """

    raise ExtractValueError(self, message)

  def extract(self):  # type: () -> Any
    return self.__datatype.extract(self)

  def store(self):  # type: () -> Any
    return self.__datatype.store(self)

  def location_info(self):  # type: () -> LocationInfo
    return LocationInfo(
      self.path,
      self.options.get('location_data'),
      self if self.options.get('attach_locator', False) else None)


class LocationInfo(object):

  def __init__(self, path, data, original):
    self.path = path
    self.data = data
    self.original = original

  def __str__(self):
    return format_location_path(self.path)


from .errors import ExtractTypeError, ExtractValueError
from .types import IDataType, AnyType


__all__ = [
  'Locator'
]
