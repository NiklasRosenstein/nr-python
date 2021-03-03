# nr.parsing.core

The `nr.parsing.core` package provides a simple API to scan and tokenize text for the purpose of
structured langauge processing.

## Example

```py
from nr.parsing.core import RuleSet, Tokenizer, rules

ruleset = RuleSet()
ruleset.rule('number', rules.regex_extract(r'\-?(0|[1-9]\d*)', 0))
ruleset.rule('operator', rules.regex_extract(r'[\-\+]', 0))
ruleset.rule('whitespace', rules.regex(r'\s+'), skip=True)

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

assert calculate('3 + 5 - 1') == 7
```

---

<p align="center">Copyright &copy; 2020 Niklas Rosenstein</p>
