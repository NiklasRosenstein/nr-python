
__author__ = 'Niklas Rosenstein <nrosenstein@palantir.com>'
__version__ = '0.1.0'

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
