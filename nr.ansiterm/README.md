# nr.ansi

  [W]: https://en.wikipedia.org/wiki/ANSI_escape_code

Module for producing ANSI escape codes and stylizing text in terminals. Supports SGR, LUT and
True colors as well as all ANSI attributes per [Wikipedia: ANSI escape code][W].

Example:

```py
from nr.ansi import styled, parse_style, Attribute
print('Hello', styled(name, 'bright_blue', attrs=['bold', 'underline']))
print(str(parse_style('%014 italic')) + "What's kickin'?" + str(Attribute.RESET))
```

---

<p align="center">Copyright &copy; 2020 Niklas Rosenstein</p>
