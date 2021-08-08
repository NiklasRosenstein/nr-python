
import typing as t
from nr.parsing.core.scanner import Cursor
from nr.parsing.core.tokenizer.tokenizer import Token
import pytest
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


def test_calculate_example():
  assert calculate('3 + 5 - 1') == 7

  with pytest.raises(ValueError) as excinfo:
    assert calculate('3 ++ 5 - 1') == 7
  assert str(excinfo.value) == "unexpected token Token(type='operator', value='+', "\
      "pos=Cursor(offset=3, line=1, column=3))"


def test_tokenize():
  assert [t.type for t in Tokenizer(ruleset, '3   +5 - 1')] == \
      ['number', 'operator', 'number', 'operator', 'number']
  assert [t.value for t in Tokenizer(ruleset, '3   +5 - 1')] == \
      ['3', '+', '5', '-', '1']


def test_zero_length_token():
  ruleset = RuleSet()
  ruleset.rule('indent', rules.regex_extract('[ ]*', at_line_start_only=True))
  ruleset.rule('name', rules.regex_extract(r'\w+'))
  ruleset.rule('ws', rules.regex_extract(' +'), skip=True)
  ruleset.rule('newline', rules.regex_extract('\n'), skip=True)

  assert [x.tv for x in list(Tokenizer(ruleset, 'foobar baz\n  spam'))] == [
    ('indent', ''), ('name', 'foobar'), ('name', 'baz'), ('indent', '  '), ('name', 'spam')]


def test_next_sentinel():
  ruleset = RuleSet(('eof', ''))
  ruleset.rule('a', rules.regex_extract('a+'))

  tok = Tokenizer(ruleset, 'aaaa')
  assert tok.next({'a', 'eof'}) == Token('a', 'aaaa', Cursor(0, 1, 0), False)
  assert tok.next({'a', 'eof'}) == Token('eof', '', Cursor(4, 1, 4), True)
