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

import typing as t

__all__ = ['ChainDict']

T = t.TypeVar('T')
K = t.TypeVar('K')
V = t.TypeVar('V')
T_ChainDict = t.TypeVar('T_ChainDict', bound='ChainDict')
_can_iteritems = lambda x: hasattr(x, 'items')
_can_iterkeys = lambda x: hasattr(x, 'keys')


class ChainDict(t.MutableMapping[K, V]):
  """
  A dictionary that wraps a list of dictionaries. The dictionaries passed
  into the #ChainDict will not be mutated. Setting and deleting values will
  happen on the first dictionary passed.
  """

  def __init__(self, main: t.MutableMapping[K, V], *others: t.Mapping[K, V]) -> None:
    self._major = main
    self._dicts: t.List[t.Mapping[K, V]] = [t.cast(t.Mapping[K, V], main)] + list(others)
    self._deleted: t.Set[K] = set()
    self._in_repr = False

  def __contains__(self, key: t.Any) -> bool:
    if key not in self._deleted:
      for d in self._dicts:
        if key in d:
          return True
    return False

  def __getitem__(self, key: K) -> V:
    if key not in self._deleted:
      for d in self._dicts:
        try: return d[key]
        except KeyError: pass
    raise KeyError(key)

  def __setitem__(self, key: K, value: V) -> None:
    self._major[key] = value
    self._deleted.discard(key)

  def __delitem__(self, key: K) -> None:
    if key not in self:
      raise KeyError(key)
    try: self._major.pop(key)
    except KeyError: pass
    self._deleted.add(key)

  def __iter__(self) -> t.Iterator[K]:
    return self.keys()

  def __len__(self) -> int:
    return sum(1 for x in self.keys())

  def __repr__(self) -> str:
    if self._in_repr:
      return 'ChainDict(...)'
    else:
      self._in_repr = True
      try:
        return 'ChainDict({})'.format(dict(self.items()))
      finally:
        self._in_repr = False

  def __eq__(self, other: t.Any) -> bool:
    return dict(self.items()) == other

  def __ne__(self, other: t.Any) -> bool:
    return not (self == other)

  @t.overload
  def get(self, key: K) -> t.Optional[V]: ...

  @t.overload
  def get(self, key: K, default: T) -> t.Union[V, T]: ...

  def get(self, key, default=None):
    try:
      return self[key]
    except KeyError:
      return default

  @t.overload  # type: ignore  # TODO (NiklasRosenstein)
  def pop(self, key: K) -> V: ...

  @t.overload
  def pop(self, key: K, default: t.Union[V, T]) -> t.Union[V, T]: ...

  def pop(self, key, default=NotImplemented):
    try:
      value = self[key]
    except KeyError:
      if default is NotImplemented:
        raise KeyError(key)
      return default
    else:
      del self[key]
    return value

  def popitem(self) -> t.Tuple[K, V]:
    if self._major:
      key, value = self._major.popitem()
      self._deleted.add(key)
      return key, value
    for d in self._dicts:
      for key in d.keys():
        if key not in self._deleted:
          self._deleted.add(key)
          return key, d[key]
    raise KeyError('popitem(): dictionary is empty')

  def clear(self) -> None:
    self._major.clear()
    self._deleted.update(self.keys())

  def copy(self: T_ChainDict) -> T_ChainDict:
    return type(self)(self._major, *self._dicts[1:])

  def setdefault(self, key: K, value: V) -> V:  # type: ignore  # TODO (NiklasRosenstein)
    try:
      return self[key]
    except KeyError:
      self[key] = value
      return value

  def update(self, E: t.Mapping[K, V], *F: t.Mapping[K, V]) -> None:  # type: ignore  # TODO (NiklasRosenstein)
    if _can_iteritems(E):
      for k, v in E.items():
        self[k] = v
    else:
      for k in E.keys():
        self[k] = E[k]
    for Fv in F:
      for k, v in Fv.items():
        self[k] = v

  def keys(self):
    seen = set()
    for d in self._dicts:
      for key in d.keys():
        if key not in seen and key not in self._deleted:
          yield key
          seen.add(key)

  def values(self):
    seen = set()
    for d in self._dicts:
      for key, value in d.items():
        if key not in seen and key not in self._deleted:
          yield value
          seen.add(key)

  def items(self):
    seen = set()
    for d in self._dicts:
      for key, value in d.items():
        if key not in seen and key not in self._deleted:
          yield key, value
          seen.add(key)
