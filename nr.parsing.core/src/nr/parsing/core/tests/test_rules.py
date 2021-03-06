
from nr.parsing.core import rules
from nr.parsing.core.scanner import Scanner


def test_string_literal():
  assert rules.string_literal().get_token(Scanner(' f"foobar"')) == None
  assert rules.string_literal().get_token(Scanner('f"foobar"')) == 'f"foobar"'
