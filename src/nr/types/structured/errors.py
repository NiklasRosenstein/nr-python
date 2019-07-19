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

class ExtractError(Exception):

  def __init__(self, locator, message=None):  # type: (Locator, Optional[str]) -> None
    self.locator = locator
    self.message = message

  def __str__(self):
    result = 'error in extract of value {}'.format(self.locator)
    if self.message:
      result += ': ' + str(self.message)
    return result


class ExtractTypeError(ExtractError):

  def __init__(self, locator, message=None):
    if message is None:
      expected = locator.datatype().readable()
      got = type(locator.value()).__name__
      message = 'expected "{}", got "{}"'.format(expected, got)
    super(ExtractTypeError, self).__init__(locator, message)


class ExtractValueError(ExtractError):
  pass


class InvalidTypeDefinitionError(Exception):

  def __init__(self, py_type_def):
    self.py_type_def = py_type_def

  def __str__(self):
    return repr(self.py_type_def)


from .locator import Locator


__all__ = [
  'ExtractError',
  'ExtractTypeError',
  'ExtractValueError',
  'InvalidTypeDefinitionError',
]
