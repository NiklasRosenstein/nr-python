
__author__ = 'Niklas Rosenstein <nrosenstein@palantir.com>'
__version__ = '0.2.0'

import typing as t

T = t.TypeVar('T')
R = t.TypeVar('R')


class flatmap(t.Generic[T, R]):
  """
  Right-hand OR operator to map a function over an optional value, only calling the function if
  the value is not None. Example:

  ```python
  >>> os.getenv('USERNAME') | flatmap(str.upper)
  ... SAMW
  >>> os.getenv('NUM_CORES') | flatmap(int)
  ... None
  ```
  """

  def __init__(self, func: t.Callable[[T], R]) -> None:
    self.func = func

  def __ror__(self, value: t.Optional[T]) -> t.Optional[R]:
    if value is not None:
      return self.func(value)
    return None


@t.overload
def coalesce(value: t.Optional[T], fallback: T) -> T: ...

@t.overload
def coalesce(value: t.Optional[T], *values: t.Optional[T]) -> t.Optional[T]: ...

@t.overload
def coalesce(value: t.Optional[T], *values: t.Optional[T], fallback: T) -> T: ...

def coalesce(value: t.Optional[T], *values: t.Optional[T], fallback: t.Optional[T] = None) -> t.Optional[T]:
  """
  Returns the first value that is not `None`. If a not-None fallback is specified, the function is guaranteed
  to return a not-Non value.
  """

  if value is not None:
    return value
  value = next((x for x in values if x is not None), None)
  if value is not None:
    return value
  return fallback
