
import datetime
import io
import re
import typing as t
from dataclasses import dataclass
from .format_options import Component, ComponentType, IFormatOption, FormatOptions

_T_datetime_format = t.TypeVar('_T_datetime_format', bound='_datetime_format')


@dataclass
class _datetime_format:
  format_str: str
  regex: re.Pattern
  seq: t.List[t.Union[str, IFormatOption]]

  @classmethod
  def compile(cls: t.Type[_T_datetime_format], format_str) -> '_T_datetime_format':
    """
    Compiles a format string to a static regex representation for fast parsing.
    """

    combo_regex = io.StringIO()
    combo_sequence: t.List[t.Union[str, IFormatOption]] = []

    idx = 0
    while idx < len(format_str):
      if format_str[idx] == '%' and len(format_str) > idx + 1:
        # TODO(NiklasRosenstein): Interpret %% as single %
        idx += 1
        char = format_str[idx]
        option = FormatOptions.get(char)
        if option is None:
          raise ValueError(f'unknown format option %{char}')
        combo_regex.write('(' + option.regex + ')')
        combo_sequence.append(option)
      else:
        char = format_str[idx]
        combo_regex.write(re.escape(char))
        if combo_sequence and isinstance(combo_sequence[-1], str):
          combo_sequence[-1] += char
        else:
          combo_sequence.append(char)
      idx += 1

    combo_regex.write('$')
    return cls(format_str, re.compile(combo_regex.getvalue()), combo_sequence)

  def __repr__(self) -> str:
    return f'{type(self).__name__}({self.format_str!r})'

  def has_component(self, component: Component) -> bool:
    return any(x.component == component for x in self.seq if isinstance(x, IFormatOption))


@dataclass
class date_format(_datetime_format):

  __repr__ = _datetime_format.__repr__

  def __post_init__(self) -> None:
    for item in self.seq:
      if isinstance(item, IFormatOption) and item.component.type != ComponentType.Date:
        raise ValueError(f'%{item.char} is an invalid format option for date_format')

  def parse_date(self, s: str) -> datetime.date:
    # TODO(NiklasRosenstein): Validate that the format string actually only captures date components.
    dt = datetime_format(self.format_str, self.regex, self.seq).parse_datetime(s)
    return dt.date()

  def format_date(self, d: datetime.date) -> str:
    # TODO(NiklasRosenstein): Validate that the format string actually only captures date components.
    dt = datetime.datetime(d.year, d.month, d.day)
    return datetime_format(self.format_str, self.regex, self.seq).format_datetime(dt)


@dataclass
class time_format(_datetime_format):

  __repr__ = _datetime_format.__repr__

  def __post_init__(self) -> None:
    for item in self.seq:
      if isinstance(item, IFormatOption) and item.component.type != ComponentType.Time:
        raise ValueError(f'%{item.char} is an invalid format option for time_format')

  def parse_time(self, s: str) -> datetime.time:
    # TODO(NiklasRosenstein): Validate that the format string actually only captures time components.
    dt = datetime_format(self.format_str, self.regex, self.seq).parse_datetime(s)
    return dt.time()

  def format_time(self, t: datetime.time) -> str:
    # TODO(NiklasRosenstein): Validate that the format string actually only captures time components.
    dt = datetime.datetime(1970, 1, 1, t.hour, t.minute, t.second, t.microsecond, t.tzinfo)
    return datetime_format(self.format_str, self.regex, self.seq).format_datetime(dt)


class datetime_format(_datetime_format):

  def parse_datetime(self, s: str) -> datetime.datetime:
    match = self.regex.match(s)
    if not match:
      raise ValueError(f'"{s}" does not match format "{self.format_str}"')
    kwargs = {'year': 1900, 'month': 1, 'day': 1, 'hour': 0}
    groups = iter(match.groups())
    for item in self.seq:
      if isinstance(item, IFormatOption):
        kwargs[item.component.value] = item.parse_string(next(groups))
    return datetime.datetime(**kwargs)  # type: ignore

  def format_datetime(self, dt: datetime.datetime) -> str:
    result = io.StringIO()
    for item in self.seq:
      if isinstance(item, str):
        result.write(item)
      else:
        result.write(item.format_value(dt, getattr(dt, item.component.value)))
    return result.getvalue()
