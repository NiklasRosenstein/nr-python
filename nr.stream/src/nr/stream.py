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

# pylint: disable=no-self-argument,not-callable

from __future__ import absolute_import

import collections
import functools
import itertools
import six

from nr.collections.abc import Mapping
from nr.pylang.utils import NotSet
from six.moves import range, filter as _filter, filterfalse as _filterfalse, zip_longest

__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
__version__ = '0.0.5'

_slice = slice
_next = next
_next_attr = 'next' if six.PY2 else '__next__'


class _dualmethod(object):
  """
  A combination of #classmethod() and instance methods. Methods decorated
  with this class can be called from the class and instance level. The first
  parameter will then refer to the class or the instance, respectively.
  """

  def __init__(self, func):
    self.func = func
    functools.update_wrapper(self, func)

  def __get__(self, instance, owner):
    assert owner is not None
    if instance is not None:
      @functools.wraps(self)
      def function(*args, **kwargs):
        return self.func(owner, instance, *args, **kwargs)
    else:
      @functools.wraps(self)
      def function(*args, **kwargs):
        return self.func(owner, *args, **kwargs)
    return function


class Stream(object):
  """
  A wrapper for iterables that provides stream processing functions. All of
  this classes methods can be accessed in a static or non-static context.
  Additionally, all of the methods are exposed in the parent module.
  """

  def __init__(self, iterable):
    self.iterable = iterable

  def __iter__(self):
    return self

  def __next__(self):
    if not hasattr(self.iterable, _next_attr):
      self.iterable = iter(self.iterable)
    return _next(self.iterable)

  def __getitem__(self, val):
    if isinstance(val, _slice):
      return self.slice(val.start, val.stop, val.step)
    elif isinstance(val, six.integer_types):
      if val >= 0:
        for index, value in enumerate(self):
          if index == val:
            return value
        raise IndexError('Stream has no element at position {}'.format(val))
      else:
        queue = collections.deque(self, maxlen=abs(val))
        if len(queue) < abs(val):
          raise IndexError('Stream has no element at position {}'.format(val))
        return queue[0]
    else:
      raise TypeError('{} object is only subscriptable with slices'.format(type(self).__name__))

  @_dualmethod
  def call(cls, iterable, *a, **kw):
    """
    Calls every item in *iterable* with the specified arguments.
    """

    return cls(x(*a, **kw) for x in iterable)

  @_dualmethod
  def map(cls, iterable, func, *a, **kw):
    """
    Iterable-first replacement of Python's built-in `map()` function.
    """

    return cls(func(x, *a, **kw) for x in iterable)

  @_dualmethod
  def flatmap(cls, iterable, func):
    """
    Same as #map() but flattens the result.
    """

    def generator():
      for x in iterable:
        for y in func(x):
          yield y
    return cls(generator())

  @_dualmethod
  def filter(cls, iterable, cond, *a, **kw):
    """
    Iterable-first replacement of Python's built-in `filter()` function.
    """

    return cls(x for x in iterable if cond(x, *a, **kw))

  @_dualmethod
  def unique(cls, iterable, key=None, skipset=None, set_type=set):
    """
    Yields unique items from *iterable* whilst preserving the original order.
    If *skipset* is specified, it must be a set of items to skip in the first
    place (ie. items to exclude from the returned stream).
    """

    if key is None:
      key = lambda x: x
    def generator():
      seen = set_type() if skipset is None else skipset
      seen_add = seen.add if hasattr(seen, 'add') else seen.append
      for item in iterable:
        key_val = key(item)
        if key_val not in seen:
          seen_add(key_val)
          yield item
    return cls(generator())

  @_dualmethod
  def chunks(cls, iterable, n, fill=None):
    """
    Collects elements in fixed-length chunks.
    """

    return cls(zip_longest(*[iter(iterable)] * n, fillvalue=fill))

  @_dualmethod
  def concat(cls, iterables):
    """
    Concatenate all iterables in *iterables* into a single stream of values.
    """

    def generator():
      for it in iterables:
        for element in it:
          yield element
    return cls(generator())

  @_dualmethod
  def chain(cls, *iterables):
    """
    Chain all of the specified iterables into a single iterable.
    """

    return cls.concat(iterables)

  @_dualmethod
  def attr(cls, iterable, attr_name):
    """
    Applies #getattr() on all elements of *iterable*.
    """

    return cls(getattr(x, attr_name) for x in iterable)

  @_dualmethod
  def item(cls, iterable, key, default=NotSet):
    """
    Applies `__getitem__` on all elements of *iterable*.
    """

    if default is NotSet:
      return cls(x[key] for x in iterable)
    else:
      return cls(x.get(key, default) for x in iterable)

  @_dualmethod
  def of_type(cls, iterable, types):
    """
    Filters using #isinstance().
    """

    return cls(x for x in iterable if isinstance(x, types))

  @_dualmethod
  def partition(cls, iterable, pred):
    """
    Use a predicate to partition items into false and true entries.
    Returns a tuple of two streams with the first containing all elements
    for which *pred* returned #False and the other containing all elements
    where *pred* returned #True.
    """

    t1, t2 = itertools.tee(iterable)
    return cls(_filterfalse(pred, t1)), cls(_filter(pred, t2))

  @_dualmethod
  def dropwhile(cls, iterable, pred):
    return cls(itertools.dropwhile(pred, iterable))

  @_dualmethod
  def takewhile(cls, iterable, pred):
    return cls(itertools.takewhile(pred, iterable))

  @_dualmethod
  def groupby(cls, iterable, key=None, collect=False):
    if collect:
      collect_as = collect if callable(collect) else list
      def generator():
        for k, g in cls.groupby(iterable, key, False):
          yield k, collect_as(g)
      return cls(generator())
    else:
      return cls(itertools.groupby(iterable, key))

  @_dualmethod
  def slice(cls, iterable, *args, **kwargs):
    return cls(itertools.islice(iterable, *args, **kwargs))

  if six.PY2:
    @_dualmethod
    def next(cls, iterable):
      if isinstance(iterable, Stream):
        return iterable.__next__()
      else:
        return _next(iter(iterable))
  else:
    @_dualmethod
    def next(cls, iterable):
      return _next(iter(iterable))

  @_dualmethod
  def length(cls, iterable):
    """
    Returns the number of items in an iterable.
    """

    iterable = iter(iterable)
    count = 0
    while True:
      try:
        _next(iterable)
      except StopIteration:
        break
      count += 1
    return count

  @_dualmethod
  def consume(cls, iterable, n=None):
    if n is not None:
      for _ in range(n):
        try:
          _next(iterable)
        except StopIteration:
          break
    else:
      while True:
        try:
          _next(iterable)
        except StopIteration:
          break
    return iterable

  @_dualmethod
  def collect(cls, iterable, collect_cls=None, *args, **kwargs):
    """
    Collects the stream into a collection.

    If *collect_cls* is not explicitly specified and the stream is currently
    wrapping a non-iterator, the wrapped object will be returned immediately.
    Otherwise, *collect_cls* defaults to [[list]].
    """

    return_wrapped = isinstance(iterable, Stream) and \
      not hasattr(iterable.iterable, _next_attr)
    if collect_cls is None and return_wrapped:
      return iterable.iterable
    else:
      return (collect_cls or list)(iterable, *args, **kwargs)

  @_dualmethod
  def batch(cls, iterable, n, collect_cls=None):
    """
    Produces a stream that yields lists of max *n* elements taken from
    *iterable*. The *collect_cls* can be overwritten to modify the collection
    type for the batched elements.

    If *collect_cls* is an identity function (`lambda x: x`), the elements
    of the new stream will be generators yielding at max *n* elements.
    """

    iterable = iter(iterable)
    if collect_cls is None:
      collect_cls = list

    def take(first):
      yield first
      count = 1
      while count < n:
        try:
          yield next(iterable)
        except StopIteration:
          break
        count += 1

    def generate_batches():
      while True:
        try:
          first = next(iterable)
        except StopIteration:
          break
        yield collect_cls(take(first))

    return cls(generate_batches())

  @_dualmethod
  def sortby(cls, iterable, by, reverse=False):
    """
    Orders the stream and returns a new [[Stream]] object that wraps the
    ordered element list. The internal list can be retrieved efficiently
    with the [[#collect()]] method.

    If *by* is a string, it will be used to look up an attribute or key.
    Otherwise, a callable is expected which is used as the sorting key.
    """

    if isinstance(by, str):
      lookup_attr = by
      def by(item):
        if isinstance(item, Mapping):
          return item[lookup_attr]
        else:
          return getattr(item, lookup_attr)

    return cls(sorted(iterable, key=by, reverse=reverse))

  @_dualmethod
  def sort(cls, iterable, reverse=False):
    return cls.sortby(iterable, lambda x: x, reverse)

  @_dualmethod
  def reduce(cls, iterable, function, initial=NotSet):
    if initial is NotSet:
      return functools.reduce(function, iterable)
    else:
      return functools.reduce(function, iterable, initial)


def _expose_members():
  for key in dir(Stream):
    if key in vars(Stream) and isinstance(vars(Stream)[key], _dualmethod):
      globals()[key] = getattr(Stream, key)
      yield key


__all__ = ['Stream'] + list(_expose_members())
