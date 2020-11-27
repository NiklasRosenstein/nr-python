# nr.parsing.core

A simple library for scanning and lexing text which makes it easy to implement new DSLs (domain
specific languages).

## Example (Scanning)

```py
from nr.parsing.core import Scanner

sc = Scanner('abc + 42.0')
assert sc.getmatch(r'\w+') == 'abc'
sc.match('\s*')
assert sc.char == '+'; sc.next()
sc.match('\s*')
assert sc.getmatch(r'\d+(?:\.\d*)') == '42.0'
assert sc.char == ''  # eof
```

## Example (Lexing)

```py
from nr.parsing.core import Scanner, Lexer, Regex, Charset

rules = [
  Charset('ws', ' ', skip=True),
  Charset('op', '+'),
  Regex('num', r'\d+(?:\.\d*)', group=0),
  Regex('id', r'\w+', group=0),
]

for tok in Lexer(Scanner('abc + 42.0'), rules):
  print(tok.type, tok.value)
```

---

<p align="center">Copyright &copy; 2020 Niklas Rosenstein</p>
