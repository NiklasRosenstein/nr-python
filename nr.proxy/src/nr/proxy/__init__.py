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

# pylint: disable=protected-access

"""
Provides the #proxy and #threadlocal type which acts as an interface to a Python object
that is usually only accessible through a function call. All attribute accesses and other
operations are forwarded to the wrapped object.
"""

import copy
import contextvars
import threading
import types
from typing import cast, Any, Callable, Generic, List, Optional, Type, TypeVar

__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
__version__ = '1.1.0'

__all__ = [
  'proxy',
  'deref_proxy',
  'threadlocal',
  'empty',
  'get',
  'set_value',
  'bind',
  'push',
  'pop',
  'make_cls',
]

T = TypeVar('T')


class proxy_base(Generic[T]):
  """
  Base class for proxy objects.
  """

  __is_proxy__ = True

  def _get_current_object(self) -> Any:
    raise NotImplementedError

  # forward special function calls and attribute access

  @property
  def __dict__(self):
    try:
      return self._get_current_object().__dict__
    except RuntimeError:
      raise AttributeError("__dict__")

  def __repr__(self):
    try:
      obj = self._get_current_object()
    except RuntimeError:
      return "<unresolvable {}.{} ({})>".format(
        type(self).__module__,
        type(self).__name__,
        get_name(self) or '<unnamed>')
    return repr(obj)

  def __bool__(self):
    try:
      return bool(self._get_current_object())
    except RuntimeError:
      return False

  def __dir__(self):
    try:
      return dir(self._get_current_object())
    except RuntimeError:
      return []

  def __getattr__(self, name):
    if name == '__members__':
      return dir(self._get_current_object())
    return getattr(self._get_current_object(), name)

  def __setitem__(self, key, value):
    self._get_current_object()[key] = value

  def __delitem__(self, key):
    del self._get_current_object()[key]

  def __call__(self, *a, **kw):
    return self._get_current_object()(*a, **kw)

  def __setattr__(self, name, value):
    if name == '__orig_class__':
      # Support for generic instantiation of the proxy type.
      object.__setattr__(self, name, value)
    else:
      setattr(self._get_current_object(), name, value)

  __delattr__ = lambda x, n: delattr(x._get_current_object(), n)  # type: ignore
  __str__ = lambda x: str(x._get_current_object())  # type: ignore
  __lt__ = lambda x, o: x._get_current_object() < o
  __le__ = lambda x, o: x._get_current_object() <= o
  __eq__ = lambda x, o: x._get_current_object() == o  # type: ignore
  __ne__ = lambda x, o: x._get_current_object() != o  # type: ignore
  __gt__ = lambda x, o: x._get_current_object() > o
  __ge__ = lambda x, o: x._get_current_object() >= o
  __hash__ = lambda x: hash(x._get_current_object())  # type: ignore
  __len__ = lambda x: len(x._get_current_object())
  __getitem__ = lambda x, i: x._get_current_object()[i]
  __iter__ = lambda x: iter(x._get_current_object())
  __contains__ = lambda x, i: i in x._get_current_object()
  __add__ = lambda x, o: x._get_current_object() + o
  __sub__ = lambda x, o: x._get_current_object() - o
  __mul__ = lambda x, o: x._get_current_object() * o
  __floordiv__ = lambda x, o: x._get_current_object() // o
  __mod__ = lambda x, o: x._get_current_object() % o
  __divmod__ = lambda x, o: x._get_current_object().__divmod__(o)
  __pow__ = lambda x, o: x._get_current_object() ** o
  __lshift__ = lambda x, o: x._get_current_object() << o
  __rshift__ = lambda x, o: x._get_current_object() >> o
  __and__ = lambda x, o: x._get_current_object() & o
  __xor__ = lambda x, o: x._get_current_object() ^ o
  __or__ = lambda x, o: x._get_current_object() | o
  __div__ = lambda x, o: x._get_current_object().__div__(o)
  __truediv__ = lambda x, o: x._get_current_object().__truediv__(o)
  __neg__ = lambda x: -(x._get_current_object())
  __pos__ = lambda x: +(x._get_current_object())
  __abs__ = lambda x: abs(x._get_current_object())
  __invert__ = lambda x: ~(x._get_current_object())
  __complex__ = lambda x: complex(x._get_current_object())
  __int__ = lambda x: int(x._get_current_object())
  __float__ = lambda x: float(x._get_current_object())
  __oct__ = lambda x: oct(x._get_current_object())
  __hex__ = lambda x: hex(x._get_current_object())
  __index__ = lambda x: x._get_current_object().__index__()
  __coerce__ = lambda x, o: x._get_current_object().__coerce__(x, o)
  __enter__ = lambda x: x._get_current_object().__enter__()
  __exit__ = lambda x, *a, **kw: x._get_current_object().__exit__(*a, **kw)
  __radd__ = lambda x, o: o + x._get_current_object()
  __rsub__ = lambda x, o: o - x._get_current_object()
  __rmul__ = lambda x, o: o * x._get_current_object()
  __rdiv__ = lambda x, o: o / x._get_current_object()
  __rtruediv__ = __rdiv__
  __rfloordiv__ = lambda x, o: o // x._get_current_object()
  __rmod__ = lambda x, o: o % x._get_current_object()
  __rdivmod__ = lambda x, o: x._get_current_object().__rdivmod__(o)
  __copy__ = lambda x: copy.copy(x._get_current_object())
  __deepcopy__ = lambda x, memo: copy.deepcopy(x._get_current_object(), memo)
  __class__ = property(lambda x: type(x._get_current_object()))  # type: ignore


class bindable_proxy(proxy_base[T]):

  def _is_bound(self) -> bool:
    raise NotImplementedError

  def _bind(self, func: Optional[Callable[[], T]]) -> None:
    raise NotImplementedError


class stackable_proxy(proxy_base[T]):

  def _empty(self) -> bool:
    raise NotImplementedError

  def _push(self, value: T) -> None:
    raise NotImplementedError

  def _pop(self) -> T:
    raise NotImplementedError


class proxy(bindable_proxy[T]):
  """
  Wraps an object returned by a callable. Every time the proxy is accessed,
  the callable is invoked and the access is redirected to the proxied object.

  > __Note__: For some use cases, using a proxy can lead to problems when
  > `isinstance()` or checks are used. For example if you pass a proxy to
  > a function that accepts an iterable, the instancecheck with
  > #collections.abc.Iterable will always return `True` as the #proxy
  > class implements the `__iter__()` method. If you are stuck with this
  > problem, use the #make_cls() function to create a new class excluding the
  > `__iter__()` method.

  ### Members
  """

  def __init__(
    self,
    local: Callable[[], T] = None,
    name: Optional[str] = None,
    lazy: bool = False,
  ) -> None:
    """
    Create a new proxy object.

    # Arguments
    local (callable): The function that will be called to retrieve the object
      represented by the proxy when demanded. This will be called again and again
      for every operation performed on the proxy, unless #lazy is enabled. If no local
      is set, the proxy is unbound. The proxy can later be bound using the #bind() function.
    name (str): The name of the proxy. Can make debugging easier if the proxy is unbound.
    lazy (bool): Call the *local* function only once on first use, then cache the result.
    """

    object.__setattr__(self, "_proxy__func", local)
    object.__setattr__(self, "_proxy__lazy", lazy)
    object.__setattr__(self, "_proxy__cache", None)
    object.__setattr__(self, "__name__", name)

  def _set(self, value: T) -> None:
    object.__setattr__(self, "_proxy__func", None)
    object.__setattr__(self, "_proxy__lazy", True)
    object.__setattr__(self, "_proxy__cache", value)

  # proxy_base

  def _get_current_object(self) -> T:
    if self.__lazy:
      if self.__cache is None:
        if self.__func is None:
          raise RuntimeError('unbound proxy')
        object.__setattr__(self, "_proxy__cache", self.__func())
      return cast(T, self.__cache)
    elif self.__func is None:
      raise RuntimeError('unbound proxy')
    else:
      return self.__func()

  def _is_bound(self) -> bool:
    return self.__func is not None

  def _bind(self, func: Optional[Callable[[], T]]) -> None:
    self.__func = func  # type: ignore


class deref_proxy(proxy):
  """
  A proxy that allows de-referencing by calling (instead of forwarding the call to the
  underlying object).
  """

  def __call__(self):
    return self._get_current_object()


class threadlocal(stackable_proxy[T]):
  """
  A proxy that contains a thread-local stack of objects.
  """

  __local: threading.local
  __error_message: Optional[str]
  __name__: Optional[str]

  def __init__(self, name: Optional[str] = None, error_message: Optional[str] = None) -> None:
    """
    Create a new thread-local proxy. If an *error_message* is provided, it will be the
    message of the #RuntimeError that will be raised if the thread local is accessed
    without being initialized in the same thread first.
    """

    object.__setattr__(self, '_threadlocal__local', threading.local())
    object.__setattr__(self, '_threadlocal__error_message', error_message)
    object.__setattr__(self, '__name__', name)

  def _get_current_object(self) -> T:
    stack: List[T] = getattr(self.__local, 'stack', None)
    if not stack:
      message = self.__error_message or 'threadlocal {name} is not initialized in this thread'
      raise RuntimeError(message.format(name=self.__name__ or '<unnamed>'))
    return stack[-1]

  def _empty(self) -> bool:
    stack: List[T] = getattr(self.__local, 'stack', None)
    return not stack

  def _push(self, value: T) -> None:
    assert value is not self, "cannot push threadlocal on itself"
    stack: List[T] = getattr(self.__local, 'stack', None)
    if stack is None:
      stack = []
      self.__local.stack = stack
    stack.append(value)

  def _pop(self) -> T:
    stack: List[T] = getattr(self.__local, 'stack', None)
    if not stack:
      name = self.__name__ or '<unnamed>'
      raise RuntimeError('there is no value to pop from threadlocal {}'.format(name))
    return stack.pop()


class contextlocal(stackable_proxy[T]):
  """
  A proxy that stores a stack of objects in a #contextvars.ContextVar (for async programs).
  """

  __contextvar: contextvars.ContextVar
  __error_message: Optional[str]
  __name__: Optional[str]

  def __init__(self, name: Optional[str] = None, error_message: Optional[str] = None) -> None:
    """
    Create a new thread-local proxy. If an *error_message* is provided, it will be the
    message of the #RuntimeError that will be raised if the thread local is accessed
    without being initialized in the same thread first.
    """

    object.__setattr__(self, '_contextlocal__contextvar', contextvars.ContextVar('local'))
    object.__setattr__(self, '_contextlocal__error_message', error_message)
    object.__setattr__(self, '__name__', name)

  def _get_current_object(self) -> T:
    stack: List[T] = self.__contextvar.get(None)
    if not stack:
      message = self.__error_message or 'contextlocal {name} is not initialized in this thread'
      raise RuntimeError(message.format(name=self.__name__ or '<unnamed>'))
    return stack[-1]

  def _empty(self) -> bool:
    stack: List[T] = self.__contextvar.get(None)
    return not stack

  def _push(self, value: T) -> None:
    assert value is not self, "cannot push contextlocal on itself"
    stack: List[T] = self.__contextvar.get(None)
    if stack is None:
      stack = []
      self.__contextvar.set(stack)
    stack.append(value)

  def _pop(self) -> T:
    stack: List[T] = self.__contextvar.get(None)
    if not stack:
      name = self.__name__ or '<unnamed>'
      raise RuntimeError('there is no value to pop from contextlocal {}'.format(name))
    return stack.pop()


def get_name(p: proxy_base[T]) -> Optional[str]:
  """
  Returns the name of a proxy object.
  """

  try:
    return cast(str, object.__getattribute__(p, '__name__'))
  except AttributeError:
    return None


def get(p: proxy_base[T]) -> T:
  """
  Dereference the proxy to get it's current value.
  """

  return p._get_current_object()


def set_value(p: proxy[T], value: T) -> None:
  """ Permanently override the value of a #proxy. This will turn the proxy "lazy". """

  p._set(value)


def bind(p: bindable_proxy[T], func: Optional[Callable[[], T]]) -> None:
  """
  (Re-) bind the function for a proxy. The *func* will be called in the future when the
  current value of the proxy is required.
  """

  p._bind(func)


def is_bound(p: bindable_proxy[T]) -> bool:
  return p._is_bound()


def empty(p: stackable_proxy[T]) -> bool:
  return p._empty()


def push(p: stackable_proxy[T], value: T) -> None:
  """
  Push a value on a stackable proxy.
  """

  p._push(value)


def pop(p: stackable_proxy[T]) -> T:
  """
  Pop a value from a stackable proxy.
  """

  return p._pop()


def make_cls(
  name: str,
  base: Type[proxy_base[T]]=None,
  include: Optional[List[str]]=None,
  exclude: Optional[List[str]]=None,
) -> Type:
  """
  Produces a new class that is the same as #proxy but does not inherit
  from it. Members can be specifically included and excluded with the
  *include*/*exclude* arguments.

  If *base* is not specified, it defaults to the #proxy class.
  """

  if base is None:
    base = cast(Type[proxy[T]], proxy)

  mro = base.__mro__
  if proxy_base not in base.__mro__:
    raise TypeError('base must be subclass of proxy_base')

  # We only want to copy the members starting with the #proxy_base class.
  members = {}
  for cls in reversed(mro[:mro.index(proxy_base)+1]):
    members.update(cls.__dict__)

  filtered_members = {}
  for key, value in members.items():
    take = False
    if include is not None and key in include:
      take = True
    elif include is None and (key.startswith('__') and key.endswith('__') or key == '_get_current_object'):
      take = True
    if exclude is not None and key in exclude:
      take = False
    if key in ['__name__', '__weakref__', '__module__', '__doc__'] \
        and (not include or key not in include):
      take = False
    if take:
      filtered_members[key] = value

  return types.new_class(name, (Generic[T],), exec_body=lambda ns: ns.update(filtered_members))  # type: ignore
