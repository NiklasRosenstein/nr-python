
import re
import typing as t
from nr.parsing.core import EofToken, RuleSet, Tokenizer, rules


ruleset: RuleSet[str, t.Any] = RuleSet()
ruleset.rule('number', rules.regex_extract(r'\-?(0|[1-9]\d*)', 0))
ruleset.rule('operator', rules.regex_extract(r'[\-\+]', 0))
ruleset.rule('whitespace', rules.regex(r'\s+'), skip=True)


def calculate(expr):
  tokenizer = Tokenizer(ruleset, expr, Tokenizer.Debug.ALL)
  print('@@', tokenizer.next())
  result = 0
  sign = 1
  while tokenizer:
    if tokenizer.current.type != 'number':
      raise ValueError(f'unexpected token {tokenizer.current}')
    result += sign * int(tokenizer.current.value)
    print('@@', tokenizer.next())
    if tokenizer.current.type == 'operator':
      sign = -1 if tokenizer.current.value == '-' else 1
      tokenizer.next()
    else:
      sign = None
  if sign is not None:
    raise ValueError(f'unexpected trailing operator')
  assert isinstance(tokenizer.current, EofToken)
  assert tokenizer.current.eof
  return result


def test_simple_tokenization():
  assert calculate('3 + 5 - 1') == 7
