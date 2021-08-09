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
import typing as t
from nr.pylang.utils import NotSet

if t.TYPE_CHECKING:
  from nr.optional import Optional

__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
__version__ = '0.2.0'

T = t.TypeVar('T')
U = t.TypeVar('U')
R = t.TypeVar('R')
Aggregator = t.Callable[[T, U], T]
Collector = t.Callable[[t.Iterable[T]], R]


class Stream(t.Generic[T], t.Iterable[T]):
  """
  A stream is an iterable with utility methods to transform it.
  """

  def __init__(self, iterable: t.Optional[t.Iterable[T]] = None) -> None:
    if iterable is None:
      iterable = ()
    self._it = iter(iterable)
    self._original: t.Optional[t.Iterable[T]] = iterable

  def __iter__(self) -> 'Stream[T]':
    return self

  def __next__(self) -> T:
    self._original = None
    return next(self._it)

  @t.overload
  def __getitem__(self, val: slice) -> 'Stream[T]': ...

  @t.overload
  def __getitem__(self, val: int) -> T: ...

  def __getitem__(self, val):
    if isinstance(val, slice):
      return self.slice(val.start, val.stop, val.step)
    elif isinstance(val, int):
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

  def next(self) -> T:
    return next(self._it)

  def append(self, *its: t.Iterable[T]) -> 'Stream[T]':
    return Stream(itertools.chain(self._it, *its))

  @t.overload
  def batch(self, n: int) -> 'Stream[t.List[T]]': ...

  @t.overload
  def batch(self, n: int, collector: Collector[T, R]) -> 'Stream[R]': ...

  def batch(self, n, collector=None):
    """
    Convert the stream into a stream of batches of size *n*, where each element of the stream
    contains the result of the *collector* after passing up to *n* elements of the original
    stream into it.
    """

    iterable = iter(self._it)
    if collector is None:
      collector = list

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
        yield collector(take(first))

    return Stream(generate_batches())

  def bipartition(self, predicate: t.Callable[[T], bool]) -> 't.Tuple[Stream[T], Stream[T]]':
    """
    Use a predicate to partition items into false and true entries.
    Returns a tuple of two streams with the first containing all elements
    for which *pred* returned #False and the other containing all elements
    where *pred* returned #True.
    """

    t1, t2 = itertools.tee(self._it)
    return Stream(itertools.filterfalse(predicate, t1)), Stream(filter(predicate, t2))

  def call(self: 'Stream[t.Callable[..., R]]', *a: t.Any, **kw: t.Any) -> 'Stream[R]':
    """
    Calls every item in *iterable* with the specified arguments.
    """

    return Stream(x(*a, **kw) for x in self._it)

  @t.overload
  def collect(self) -> t.List[T]: ...

  @t.overload
  def collect(self, collector: Collector[T, R]) -> R: ...

  def collect(self, collector=list):
    """
    Collects the stream into a collection.
    """

    if isinstance(collector, type) and isinstance(self._original, collector):
      # NOTE(NiklasRosenstein): This is an optimization to retrieve the original underlying
      #   collection if the stream has not been advanced yet.
      return self._original

    return collector(self._it)

  def count(self) -> int:
    """
    Returns the number of items in the stream. This fully consumes the stream.
    """

    count = 0
    while True:
      try:
       next(self._it)
      except StopIteration:
        break
      count += 1
    return count

  def concat(self: 't.Iterable[t.Iterable[T]]') -> 'Stream[T]':  # https://github.com/python/mypy/issues/10517
    """
    Concatenate all values in the stream into a single stream of values.
    """

    def generator():
      for it in self:
        for element in it:
          yield element
    return Stream(generator())

  def consume(self, n: t.Optional[int] = None) -> 'Stream[T]':
    """
    Consume the contents of the stream, up to *n* elements if the argument is specified.
    """

    if n is not None:
      for _ in range(n):
        try:
          next(self._it)
        except StopIteration:
          break
    else:
      while True:
        try:
          next(self._it)
        except StopIteration:
          break
    return self

  def distinct(self,
    key: t.Optional[t.Callable[[T], t.Any]] = None,
    skip: t.Union[t.MutableSet[T], t.MutableSequence[T], None] = None,
  ) -> 'Stream[T]':
    """
    Yields unique items from *iterable* whilst preserving the original order. If *skip* is
    specified, it must be a set or sequence of items to skip in the first place (ie. items to
    exclude from the returned stream). The specified set/sequence is modified in-place. Using a
    set is highly recommended for performance purposes.
    """

    if key is None:
      key_func = lambda x: x
    else:
      key_func = key

    def generator() -> t.Generator[T, None, None]:
      seen = set() if skip is None else skip
      mark_visited = seen.add if isinstance(seen, t.MutableSet) else seen.append
      check_visited = seen.__contains__
      for item in self._it:
        key_val = key_func(item)
        if not check_visited(key_val):
          mark_visited(key_val)
          yield item

    return Stream(generator())

  def dropwhile(self, predicate: t.Callable[[T], bool]) -> 'Stream[T]':
    return Stream(itertools.dropwhile(predicate, self._it))

  def dropnone(self: 'Stream[t.Optional[T]]') -> 'Stream[T]':
    return Stream(x for x in self._it if x is not None)

  def filter(self, predicate: t.Callable[[T], bool]) -> 'Stream[T]':
    """
    Agnostic to Python's built-in `filter()` function.
    """

    return Stream(x for x in self._it if predicate(x))

  def first(self) -> t.Optional[T]:
    """
    Returns the first element of the stream, or `None`.
    """

    try:
      return self.next()
    except StopIteration:
      return None

  def firstopt(self) -> 'Optional[T]':
    """
    Returns the first element of the stream as an `Optional`.
    """

    from nr.optional import Optional
    return Optional(self.first())

  def flatmap(self, func: t.Callable[[T], t.Iterable[R]]) -> 'Stream[R]':
    """
    Same as #map() but flattens the result.
    """

    def generator() -> t.Generator[R, None, None]:
      for x in self._it:
        for y in func(x):
          yield y
    return Stream(generator())

  @t.overload
  def groupby(self, key: t.Callable[[T], R]) -> 'Stream[t.Tuple[R, t.Iterable[T]]]': ...

  @t.overload
  def groupby(self, key: t.Callable[[T], R], collector: Collector[T, R]) -> 'Stream[t.Tuple[R, U]]': ...

  def groupby(self, key: t.Callable[[T], R], collector: t.Optional[Collector[T, R]] = None):
    if collector is None:
      return Stream(itertools.groupby(self._it, key))
    else:
      def generator():
        assert collector is not None
        g: t.Iterable[T]
        for k, g in self.groupby(key, lambda x: x):
          yield k, collector(g)
      return Stream(generator())

  def map(self, func: t.Callable[[T], R]) -> 'Stream[R]':
    """
    Agnostic to Python's built-in `map()` function.
    """

    return Stream(func(x) for x in self._it)

  def of_type(self, type: t.Type[T]) -> 'Stream[T]':
    """
    Filters using #isinstance().
    """

    return Stream(x for x in self._it if isinstance(x, type))

  @t.overload
  def reduce(self, aggregator: Aggregator[T, T]) -> T: ...

  @t.overload
  def reduce(self, aggregator: Aggregator[R, T], initial: R) -> R: ...

  def reduce(self, aggregator, initial=NotSet.Value):
    if initial is NotSet.Value:
      return functools.reduce(aggregator, self._it)
    else:
      return functools.reduce(aggregator, self._it, initial)

  @t.overload
  def slice(self, stop: int) -> 'Stream[T]': ...

  @t.overload
  def slice(self, start: int, stop: int, step: int = 1) -> 'Stream[T]': ...

  def slice(self, *a, **kw):
    return Stream(itertools.islice(self._it, *a, **kw))

  def sortby(self, by: t.Union[str, t.Callable[[T], t.Any]], reverse: bool = False) -> 'Stream[T]':
    """
    Creates a new sorted stream. Internally the #sorted() built-in function is used so a new list
    will be created temporarily.

    # Parameters
    by (str, callable): Specify by which dimension to sort the stream. If a string is specified,
      it will be used to retrieve a key or attribute from the values in the stream. In the case of
      a callable, it will be used directly as the `key` argument to #sorted().
    """

    if isinstance(by, str):
      lookup_attr = by
      def by(item):
        if isinstance(item, t.Mapping):
          return item[lookup_attr]
        else:
          return getattr(item, lookup_attr)

    by = t.cast(t.Callable[[T], t.Any], by)
    return Stream(sorted(self._it, key=by, reverse=reverse))

  def sort(self, reverse: bool = False) -> 'Stream[T]':
    return self.sortby(lambda x: x, reverse)

  def takewhile(self, predicate: t.Callable[[T], bool]) -> 'Stream[T]':
    return Stream(itertools.takewhile(predicate, self._it))
