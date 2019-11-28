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

__all__ = ['Path', 'Location']


class Path(object):
  """ Represents a chain of keys/indices to represent the position of a value
  in a structured object. This object is immutable. """

  ROOT_ELEMENT = '$'
  ALLOWED_KEY_CHARS = string.ascii_letters + string.digits + '_-'

  def __init__(self, items):
    self._items = items

  def __iter__(self):
    return iter(self._items)

  def __len__(self):
    return len(self._items)

  def __getitem__(self, index):
    return self._items[index]

  def __str__(self):

    def generate():
      yield Path.ROOT_ELEMENT
      for key in self._items:
        if isinstance(key, int):
          yield '[{}]'.format(key)
        else:
          escaped_key = str(key)
          if '"' in escaped_key:
            escaped_key = escaped_key.replace('"', '\\"')
          if any(c not in Path.ALLOWED_KEY_CHARS for c in escaped_key):
            escaped_key = '"' + escaped_key + '"'
          yield '.' + escaped_key

    return ''.join(generate())

  def to_location(self, value, datatype):
    """ Creates a new chain of #Location objects of this path. All locations
    except for the final one contain no value or datatype. """

    parent = None
    for item in self._items[:-1]:
      parent = Location(parent, item, None, None)
    return Location(parent, self._items[-1] if self._items else None, value, datatype)

  def resolve(self, value): # type: (Union[List, Dict]) -> Any
    """ Returns the value at this path by subsequently accessing every item in
    the path in *value* and its child nested structures.

    Example:

    ```py
    path = Path(['a', 1, 'foo'])
    data = {'a': [{'foo': 1}, {'foo': 2}]}
    assert path.resolve(data) == 2
    ``` """

    for item in self._items:
      try:
        value = value[item]
      except KeyError as exc:
        raise KeyError(str(self))
      except IndexError as exc:
        raise IndexError('{} at {}'.format(exc, self))
    return value


class Location(object):
  """ A container for the position of a value in a nested structure as well
  as the value itself and the expected datatype for that value. """

  def __init__(self, value, datatype, path):
    # type: (Any, IDataType, Path)
    self.value = value
    self.datatype = datatype
    self.path = path

  def __repr__(self):
    return '<Location at {} of {}>'.format(self.path, self.datatype)
