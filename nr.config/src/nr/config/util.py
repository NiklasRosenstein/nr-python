# -*- coding: utf8 -*-
# Copyright (c) 2020 Niklas Rosenstein
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

from collections import abc
from nr.pylang.utils.classdef import make_singleton
from typing import Any, List, Union
import copy
import re


class AccessorList:

  #: This is a special singleton return by #parse_accessor_string() to represent
  #: a wildcard index.
  WILDCARD = make_singleton('WILDCARD')
  Key = Union[str, int, type(WILDCARD)]

  def __init__(self, access_list: Union[str, List[Key]]) -> None:
    if isinstance(access_list, str):
      self._items = self._parse(access_list)
    else:
      self._items = list(access_list)

  def __repr__(self):
    def _format(x):
      if x is AccessorList.WILDCARD:
        return '*'
      elif isinstance(x, int):
        return '[{}]'.format(x)
      else:
        return '.' + x
    return '$' + ''.join(map(_format, self._items))

  @staticmethod
  def _parse(s: str) -> List[Key]:
    result = []
    for part in s.split('.'):
      match = re.match(r'(.*)\[(\d+|\*)\]', part)
      if match:
        result.append(match.group(1))
        result.append(AccessorList.WILDCARD if match.group(2) == '*' else int(match.group(2)))
      else:
        result.append(part)
    return result

  def __call__(self, data: Any) -> Any:
    """
    Resolve the items in the accessor list on *data*. If the accessor list contains a
    wildcard, a list of values will be returned.
    """

    it = iter(self._items)
    for item in it:
      if item == AccessorList.WILDCARD:
        # TODO: Verify that *item* is a sequence?
        sub_list = AccessorList(it)
        data = [sub_list(v) for v in data]
        break
      else:
        data = data[item]

    return data

  def __add__(self, other: 'AccessorList') -> 'AccessorList':
    if not isinstance(other, AccessorList):
      return NotImplemented
    return AccessorList(self._items + other._items)


def merge_dicts(a: Any, b: Any, path: str = '$', exclude_key: str = '{{exclude}}'):
  """
  Recursively merges two dictionaries, applying the keys of *b* over *a*.
  """

  if isinstance(a, abc.Mapping):
    if not isinstance(b, abc.Mapping):
      raise ValueError('Unable to merge incompatible types "{}" and "{}" at {}'
                       .format(type(a).__name__, type(b).__name__, path))

    a = copy.copy(a)
    for key in b:
      if b[key] == exclude_key:
        if key in a:
          del a[key]
        continue
      if key in a:
        a[key] = merge_dicts(a[key], b[key], path + '.' + key)
      else:
        a[key] = b[key]

    return a

  return b
