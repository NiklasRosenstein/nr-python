
import re
import typing as t
from nr.parsing.core import RuleSet, Tokenizer, rules


ruleset = RuleSet()
ruleset.rule('number', rules.regex_extract(r'\-?(0|[1-9]\d*)'))
ruleset.rule('operator', rules.regex_extract(r'[\-\+]'))
ruleset.rule('whitespace', rules.regex_extract(r'\s+'), skip=True)


def calculate(expr: str) -> int:
  tokenizer = Tokenizer(ruleset, expr)
  result = 0
  sign: t.Optional[int] = 1
  while tokenizer:
    if tokenizer.current.type != 'number':
      raise ValueError(f'unexpected token {tokenizer.current}')
    assert sign is not None
    result += sign * int(tokenizer.current.value)
    tokenizer.next()
    if tokenizer.current.type == 'operator':
      sign = -1 if tokenizer.current.value == '-' else 1
      tokenizer.next()
    else:
      sign = None
  if sign is not None:
    raise ValueError(f'unexpected trailing operator')
  return result


def test_simple_tokenization():
  assert calculate('3 + 5 - 1') == 7
