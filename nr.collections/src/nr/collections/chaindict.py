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
import six

__all__ = ['ChainDict']

if six.PY2:
  _can_iteritems = lambda x: hasattr(x, 'iteritems')
  _can_iterkeys = lambda x: hasattr(x, 'keys')
else:
  _can_iteritems = lambda x: hasattr(x, 'items')
  _can_iterkeys = lambda x: hasattr(x, 'keys')


class ChainDict(abc.MutableMapping):
  """
  A dictionary that wraps a list of dictionaries. The dictionaries passed
  into the #ChainDict will not be mutated. Setting and deleting values will
  happen on the first dictionary passed.
  """

  def __init__(self, *dicts):
    if not dicts:
      raise ValueError('need at least one argument')
    self._major = dicts[0]
    self._dicts = list(dicts)
    self._deleted = set()
    self._in_repr = False

  def __contains__(self, key):
    if key not in self._deleted:
      for d in self._dicts:
        if key in d:
          return True
    return False

  def __getitem__(self, key):
    if key not in self._deleted:
      for d in self._dicts:
        try: return d[key]
        except KeyError: pass
    raise KeyError(key)

  def __setitem__(self, key, value):
    self._major[key] = value
    self._deleted.discard(key)

  def __delitem__(self, key):
    if key not in self:
      raise KeyError(key)
    self._major.pop(key, None)
    self._deleted.add(key)

  def __iter__(self):
    return six.iterkeys(self)

  def __len__(self):
    return sum(1 for x in self.keys())

  def __repr__(self):
    if self._in_repr:
      return 'ChainDict(...)'
    else:
      self._in_repr = True
      try:
        return 'ChainDict({})'.format(dict(six.iteritems(self)))
      finally:
        self._in_repr = False

  def __eq__(self, other):
    return dict(self.items()) == other

  def __ne__(self, other):
    return not (self == other)

  def get(self, key, default=None):
    try:
      return self[key]
    except KeyError:
      return default

  def pop(self, key, default=NotImplemented):
    if key not in self:
      if default is NotImplemented:
        raise KeyError(key)
      return default
    self._major.pop(key, None)
    self._deleted.add(key)

  def popitem(self):
    if self._major:
      key, value = self._major.popitem()
      self._deleted.add(key)
      return key, value
    for d in self._dicts:
      for key in six.iterkeys(d):
        if key not in self._deleted:
          self._deleted.add(key)
          return key, d[key]
    raise KeyError('popitem(): dictionary is empty')

  def clear(self):
    self._major.clear()
    self._deleted.update(six.iterkeys(self))

  def copy(self):
    return type(self)(*self._dicts[1:])

  def setdefault(self, key, value=None):
    try:
      return self[key]
    except KeyError:
      self[key] = value
      return value

  def update(self, E, *F):
    if _can_iteritems(E):
      for k, v in six.iteritems(E):
        self[k] = v
    elif _can_iterkeys(E):
      for k in six.iterkeys(E):
        self[k] = E[k]
    elif hasattr(E, 'items'):
      E = E.items()
    for k, v in E:
      self[k] = v
    for Fv in F:
      for k, v in six.iteritems(Fv):
        self[k] = v

  def keys(self):
    seen = set()
    for d in self._dicts:
      for key in six.iterkeys(d):
        if key not in seen and key not in self._deleted:
          yield key
          seen.add(key)

  def values(self):
    seen = set()
    for d in self._dicts:
      for key, value in six.iteritems(d):
        if key not in seen and key not in self._deleted:
          yield value
          seen.add(key)

  def items(self):
    seen = set()
    for d in self._dicts:
      for key, value in six.iteritems(d):
        if key not in seen and key not in self._deleted:
          yield key, value
          seen.add(key)

  if six.PY2:
    iterkeys = keys
    keys = lambda self: list(self.iterkeys())
    itervalues = values
    values = lambda self: list(self.itervalues())
    iteritems = items
    items = lambda self: list(self.iteritems())
