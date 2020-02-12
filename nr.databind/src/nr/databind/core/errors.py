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

from .location import Location

__all__ = [
  'SerializationError',
  'SerializationTypeError',
  'SerializationValueError',
  'InvalidTypeDefinitionError'
]


class SerializationError(Exception):

  def __init__(self, location, message=None):  # type: (Location, Optional[str])
    if not isinstance(location, Location):
      raise TypeError('location must be a Location object, got {}'.format(
        type(location).__name__))
    self.location = location
    self.message = message

  def __str__(self):
    result = 'at {}'.format(self.location.path)
    if self.location.filename:
      result = 'in "{}": '.format(self.location.filename) + result
    if self.message:
      result += ': ' + str(self.message)
    return result


class SerializationTypeError(SerializationError):

  def __init__(self, location, message=None):  # type: (Location, Optional[str])
    if message is None:
      expected = location.datatype.to_human_readable()
      got = type(location.value).__name__
      message = 'expected "{}", got "{}"'.format(expected, got)
    super(SerializationTypeError, self).__init__(location, message)


class SerializationValueError(SerializationError):
  pass


class InvalidTypeDefinitionError(Exception):

  def __init__(self, py_type_def):
    self.py_type_def = py_type_def

  def __str__(self):
    return repr(self.py_type_def)
