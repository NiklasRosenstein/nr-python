# nr.parsing.core

The `nr.parsing.core` package provides a simple API to scan and tokenize text for the purpose of
structured langauge processing.

## Example

```py
from nr.parsing.core import Lexer, rules

lexer = Lexer()
lexer.rule('number', rules.regex_extract(r'\-?(0|[1-9]\d*)', 0))
lexer.rule('operator', rules.regex_extract(r'[\-\+]', 0))
lexer.rule('whitespace', rules.regex(r'\s+'), skip=True)

def calculate(expr):
  tokenizer = lexer.create_tokenizer(expr)
  result = 0
  sign = 1
  while tokenizer:
    if tokenizer.current.type != 'number':
      raise ValueError(f'unexpected token {tokenizer.current}')
    result += sign * int(tokenizer.current.value)
    tokenizer.next()
    if tokenizer.current.type == 'operator':
      sign = -1 if tokenizer.current.value == '-' else 1
    else:
      sign = None
  if sign is not None:
    raise ValueError(f'unexpected trailing operator') 
  return result

assert calculate('3 + 5 - 1') == 7
```

---

<p align="center">Copyright &copy; 2020 Niklas Rosenstein</p>
