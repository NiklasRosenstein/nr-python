
import contextlib
import typing as t
from dataclasses import dataclass

from ..scanner import Scanner

if t.TYPE_CHECKING:
  from .extractor import TokenExtractor

T = t.TypeVar('T')
U = t.TypeVar('U')
V = t.TypeVar('V')
R = t.TypeVar('R')


@dataclass
class Rule(t.Generic[T, U]):
  type: T
  extractor: 'TokenExtractor[U]'
  skip: bool


class RuleSet(t.Generic[T, U]):
  """
  A ordered list of parsing rules that is used a the #Tokenizer.
  """

  def __init__(self) -> None:
    self._rules: t.List[Rule[T, U]] = []
    self._token_types: t.Set[T] = set()

  def __iter__(self) -> t.Iterator[Rule]:
    return iter(self._rules)

  @property
  def rules(self) -> t.List[Rule]:
    return list(self._rules)

  @property
  def token_types(self) -> t.Set[T]:
    return self._token_types

  def has_token_type(self, token_type: T) -> bool:
    return token_type in self._token_types

  def check_has_token_types(self, token_types: t.Set[T]) -> None:
    delta = token_types - self._token_types
    if delta:
      raise ValueError(f'unknown token types: {", ".join(map(str, delta))}')

  def rule(self, type_: T, extractor: 'TokenExtractor[U]', skip: bool = False) -> 'RuleSet[T, U]':
    """ Add a rule and return self. """

    self._rules.append(Rule(type_, extractor, skip))
    self._token_types.add(type_)
    return self


class RuleConfigSet(t.Generic[T, U, V]):
  """ Helper class to manage values associated with token types. """

  def __init__(self, rules: 'RuleSet[T, U]') -> None:
    self._rules = rules
    self._values: t.Dict[T, V] = {}

  def set(self, token_types: t.Union[T, t.Collection[T]], value: V) -> t.ContextManager[None]:
    """
    Set the value of one or more token types. The returned context manager _may_ be used, but
    does not _have_ to be used, to revert to the previous state.

    Implementation detail: strings are not considered collections when identifying the type
    of the *token_types* argument.
    """

    if isinstance(token_types, str) or not isinstance(token_types, t.Collection):
      token_types_set = frozenset([t.cast(T, token_types)])
    else:
      token_types_set = frozenset(token_types)

    current_values = {k: v for k, v in self._values.items() if k in token_types_set}

    for token_type in token_types_set:
      if not self._rules.has_token_type(token_type):
        raise ValueError(f'not a possible token type: {token_type!r}')

    for token_type in token_types_set:
      self.set(token_type, value)

    @contextlib.contextmanager
    def _revert() -> t.Iterator[None]:
      try: yield
      finally:
        for token_type in token_types_set:
          if token_type not in current_values:
            # NOTE(NiklasRosenstein): https://github.com/python/mypy/issues/10152
            self._values.pop(token_type, None)  # type: ignore
          else:
            self.set(token_type, current_values[token_type])

    return _revert()

  def get(self, token_type: T, default: R) -> t.Union[V, R]:
    return self._values.get(token_type, default)
