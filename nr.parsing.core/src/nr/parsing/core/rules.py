
import re
import typing as t

from nr.parsing.core.tokenizer import TokenExtractor

if t.TYPE_CHECKING:
  from nr.parsing.core.scanner import Scanner


def regex(pattern: str, *, at_line_start_only: bool = False) -> TokenExtractor[re.Match]:
  """
  Creates a tokenizer rule that matches a regular expression and returns the #re.Match object
  as the token value. If you want the pattern to match at the start of a line only, set the
  *at_line_start_only* argument to `True`. The regex caret (`^`) control character will not work
  because the regex is matched from the cursor's current position and not the line start.
  """

  def _impl(scanner: 'Scanner') -> t.Optional[re.Match]:
    if at_line_start_only and scanner.pos.column != 0:
      return None
    match = scanner.match(pattern)
    if match is None:
      return None
    return match

  return TokenExtractor.of(_impl)


def regex_extract(pattern: str, group: t.Union[str, int], *,
    at_line_start_only: bool = False) -> TokenExtractor[str]:
  """
  Creates a tokenizer rule that matches a regular expression and extracts a group from the
  match as the token value.
  """

  return regex(pattern, at_line_start_only=at_line_start_only).map(lambda m: m.group(group))
