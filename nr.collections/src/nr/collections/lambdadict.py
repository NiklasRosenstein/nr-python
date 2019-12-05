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

from . import abc


class LambdaDict(abc.MutableMapping):

  def __init__(self, getter, setter=None, deleter=None, length=None, iterate=None):
    self._getter = getter
    self._setter = setter
    self._deleter = deleter
    self._length = length
    self._iterate = iterate

  def __getitem__(self, key):
    return self._getter(key)

  def __setitem__(self, key, value):
    if self._setter is None:
      raise NotImplementedError('__setitem__() not configured')
    self._setter(key, value)

  def __delitem__(self, key):
    if self._deleter is None:
      raise NotImplementedError('__delitem__() not configured')
    self._deleter(key)

  def __len__(self):
    if self._length is None:
      raise NotImplementedError('__len__() not configured')
    return self._length()

  def __iter__(self):
    if self._iterate is None:
      raise NotImplementedError('__iter__() not configured')
    return self._iterate()
