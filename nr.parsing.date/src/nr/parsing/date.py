# -*- coding: utf8 -*-
# Copyright (c) 2019 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

"""
A fast date parser library with timezone offset support.
"""

from datetime import datetime, timedelta, tzinfo
from itertools import chain
from nr.utils.re import match_all  # type: ignore
import abc
import importlib
import io
import os
import re
import typing as t

re = importlib.import_module(os.getenv('PYTHON_NR_DATE_REGEX_BACKEND', 're'))  # type: ignore

if t.TYPE_CHECKING:
  import dateutil.relativedelta

__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
__version__ = '0.6.0'


class timezone(tzinfo):
  """
  A simple implementation of #datetime.tzinfo.
  """

  utc: 'timezone'
  local: 'timezone'

  _ZERO = timedelta(0)

  def __init__(self, name: t.Optional[str], offset: t.Union[timedelta, float]) -> None:
    seconds = offset.total_seconds() if isinstance(offset, timedelta) else float(offset)
    self._offset = timedelta(seconds=seconds)
    self._name = name
    if offset == 0 and not self._name:
      self._name = 'UTC'

  def dst(self, dt: t.Optional[datetime]) -> timedelta:
    return self._ZERO

  def utcoffset(self, dt: t.Optional[datetime]) -> timedelta:
    return self._offset

  def tzname(self, dt: t.Optional[datetime]) -> t.Optional[str]:
    return self._name

  def fromutc(self, dt: datetime) -> datetime:
    return dt + self._offset

  def __repr__(self) -> str:
    if self._name == 'UTC':
      return 'timezone.utc'
    else:
      return 'timezone({!r}, {!r})'.format(self._name, self._offset.total_seconds())

  def __eq__(self, other) -> bool:
    if not isinstance(other, timezone):
      return NotImplemented
    return self._offset == other._offset

  def __ne__(self, other) -> bool:
    return not (self == other)

  def __hash__(self) -> int:
    return hash((type(self), self._offset))


timezone.utc = timezone('UTC', 0)
timezone.local = timezone('local', (datetime.now() - datetime.utcnow()).total_seconds())


class BaseFormatOption:

  def __init__(self, char: str, dest: str, regex: 're.Pattern') -> None:
    self.char = char
    self.dest = dest
    self.regex = regex

  def parse(self, string: str) -> t.Any:
    raise NotImplementedError

  def render(self, date: datetime) -> t.Any:
    raise NotImplementedError


class FormatOption(BaseFormatOption):

  def __init__(self, char: str, dest: str, regex: str, parse: t.Callable[[str], int], render: t.Callable[[datetime], str]) -> None:
    super(FormatOption, self).__init__(char, dest, re.compile(regex))
    self.parse = parse  # type: ignore
    self.render = render  # type: ignore


class TimezoneFormatOption(BaseFormatOption):

  def __init__(self, char: str = 'z', dest: str = 'tzinfo') -> None:
    super(TimezoneFormatOption, self).__init__(char, dest, re.compile(r'(?:Z|[-+]\d{2}:?\d{2})'))

  def parse(self, string: str) -> tzinfo:
    match = self.regex.match(string)
    if not match:
      raise ValueError('not a timezone string: {!r}'.format(string))
    if string == 'Z':
      return timezone.utc
    else:
      string = string.replace(':', '')
      sign = -1 if string[0] == '-' else 1
      hours = int(string[1:3])
      minutes = int(string[3:5])
      seconds = sign * (hours * 3600 + minutes * 60)
      return timezone(None, seconds)

  def render(self, date: datetime) -> str:
    if date.tzinfo == None:
      raise ValueError('no tzinfo in date: {!r}'.format(date))
    elif date.tzinfo == timezone.utc:
      return 'Z'
    else:
      utcoffset = date.utcoffset()
      # NOTE Copied from CPython 3.7 datetime.py _format_offset()
      string = ''
      if utcoffset is not None:
        if utcoffset.days < 0:
          sign = "-"
          utcoffset = -utcoffset
        else:
          sign = "+"
        off = utcoffset.total_seconds()
        hh, mm = divmod(off, 60 * 60)
        mm, ss = divmod(mm, 60)
        ss, ms = divmod(ss, 1)
        string += "%s%02d:%02d" % (sign, hh, mm)
        if ss or ms:
          string += ":%02d" % ss
          if ms:
            string += '.%06d' % ms
      return string


class DatetimeFormat(metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def parse(self, string: str) -> datetime:
    pass

  @abc.abstractmethod
  def format(self, datetime: datetime) -> str:
    pass


class FormatOptionSet:

  def __init__(self, options: t.Collection[BaseFormatOption] = ()):
    self._options: t.Dict[str, 'BaseFormatOption'] = {}
    self._cache: t.Dict[str, 'DatetimeFormat'] = {}
    for option in options:
      self.add(option)

  def __repr__(self) -> str:
    return 'FormatOptionSet({})'.format(''.join(sorted(self._options)))

  def __getitem__(self, char: str) -> 'BaseFormatOption':
    return self._options[char]

  def __contains__(self, char: str) -> bool:
    return char in self._options

  def add(self, option: BaseFormatOption) -> None:
    if not isinstance(option, BaseFormatOption):
      raise TypeError('expected BaseFormatOption')
    if option.char in self._options:
      raise ValueError('format char {!r} already allocated'.format(option.char))
    self._options[option.char] = option

  def create_date_format(self, fmt: str) -> 'DatetimeFormat':
    # TODO @NiklasRosenstein Work around cyclic reference, eg. with a weakref?
    try:
      return self._cache[fmt]
    except KeyError:
      obj = self._cache[fmt] = CompiledDatetimeFormat(fmt, self)
      return obj

  def create_format_set(self, name: str, formats: t.Iterable[t.Union[str, 'DatetimeFormat']]) -> 'DatetimeFormatSet':
    return DatetimeFormatSet(name, [self.create_date_format(x)
      if not isinstance(x, DatetimeFormat) else x for x in formats])

  def parse(self, string: str, fmt: str) -> datetime:
    return self.create_date_format(fmt).parse(string)

  def format(self, date: datetime, fmt: str) -> str:
    return self.create_date_format(fmt).format(date)


class CompiledDatetimeFormat(DatetimeFormat):
  """
  Represents a fully compiled fixed date format ready to parse and
  format dates.
  """

  def __init__(self, string: str, option_set: FormatOptionSet) -> None:
    index = 0
    pattern = io.StringIO()
    options = []
    join_sequence: t.List[t.Union[str, BaseFormatOption]] = []

    def write(char, escaped=False):
      pattern.write(char if char in '()?%' else re.escape(char))
      if char == '(':
        pattern.write('?:')  # Make exernal group optional
      if char in '()?%' and not escaped:
        return
      if join_sequence and isinstance(join_sequence[-1], str):
        join_sequence[-1] += char
      else:
        join_sequence.append(char)

    while index < len(string):
      if string[index] == '%':
        char = string[index+1]
        if char in '()?%':
          write(char)
        elif char not in option_set:
          raise ValueError('Invalid date format "%{}"'.format(char))
        else:
          fo = option_set[char]
          pattern.write('(' + fo.regex.pattern + ')')
          options.append(fo)
          join_sequence.append(fo)
        index += 2
      else:
        write(string[index])
        index += 1

    self._string = string
    self._regex = re.compile(pattern.getvalue())
    self._join_sequence = join_sequence
    self._options = options

  def __repr__(self) -> str:
    return 'CompiledDatetimeFormat(string={!r})'.format(self.string)

  @property
  def string(self) -> str:
    return self._string

  def parse(self, string: str) -> datetime:
    match = self._regex.match(string)
    if not match:
      raise ValueError('Date "{}" does not match format {!r}'.format(
        string, self.string))
    kwargs = {'year': 1900, 'month': 1, 'day': 1, 'hour': 0}
    for option, value in zip(self._options, match.groups()):
      if value is not None:
        kwargs[option.dest] = option.parse(value)
    return datetime(**kwargs)  # type: ignore

  def format(self, date: datetime) -> str:
    result = io.StringIO()
    for item in self._join_sequence:
      if isinstance(item, str):
        result.write(item)
      else:
        result.write(item.render(date))
    return result.getvalue()


class DatetimeFormatSet(list, DatetimeFormat):
  """
  Represents a set of date formats.
  """

  def __init__(self, name: str, formats: t.List[DatetimeFormat]) -> None:
    super(DatetimeFormatSet, self).__init__(formats)
    self.name = name

  def __repr__(self) -> str:
    return 'DatetimeFormatSet({!r}, {})'.format(
      self.name, super(DatetimeFormatSet, self).__repr__())

  def parse(self, string: str) -> datetime:
    for fmt in self:
      try:
        return fmt.parse(string)
      except ValueError:
        pass
    msg = 'Date "{}" does not match any of the {!r} formats.\n- {}'
    formats = '\n- '.join(x.string for x in self)
    raise ValueError(msg.format(string, self.name, formats))

  def format(self, date: datetime) -> str:
    errors = []
    for fmt in self:
      try:
        return fmt.format(date)
      except ValueError as exc:
        errors.append(exc)
    msg = 'Date "{}" cannot be formatted with any of the {!r} formats.\n- {}'
    formats = '\n- '.join('{}: {}'.format(x.string, e) for x, e in zip(self, errors))
    raise ValueError(msg.format(date, self.name, formats))


root_option_set = FormatOptionSet([
    FormatOption('Y', 'year', r'\d{4}', int, lambda d: str(d.year).rjust(4, '0')),
    FormatOption('m', 'month', r'\d{2}', int, lambda d: str(d.month).rjust(2, '0')),
    FormatOption('d', 'day', r'\d{2}', int, lambda d: str(d.day).rjust(2, '0')),
    FormatOption('H', 'hour', r'\d{2}', int, lambda d: str(d.hour).rjust(2, '0')),
    FormatOption('M', 'minute', r'\d{2}', int, lambda d: str(d.minute).rjust(2, '0')),
    FormatOption('S', 'second', r'\d{2}', int, lambda d: str(d.second).rjust(2, '0')),
    FormatOption(
      'f', 'microsecond', r'\d+',
      parse=lambda s: int(str(int(s) * (10 ** max(6-len(s), 0)))[:6]),  # Truncate higher precisions that microseconds
      render=lambda d: str(d.microsecond).rjust(6, '0').rstrip('0') or '0'
    ),
    TimezoneFormatOption(),
])


def register_format_option(option: BaseFormatOption) -> None:
  root_option_set.add(option)


def parse_date(string: str, fmt: str) -> datetime:
  return root_option_set.parse(string, fmt)


def format_date(date: datetime, fmt: str) -> str:
  return root_option_set.format(date, fmt)


class Duration(object):
  """
  Represents an ISO8601 duration.
  """

  _fields = ['years', 'months', 'weeks', 'days', 'hours', 'minutes', 'seconds']

  def __init__(self, years: int = 0, months: int = 0, weeks: int = 0, days: int = 0,
               hours: int = 0, minutes: int = 0, seconds: int = 0) -> None:
    self.years = years
    self.months = months
    self.weeks = weeks
    self.days = days
    self.hours = hours
    self.minutes = minutes
    self.seconds = seconds
    for k in self._fields:
      if getattr(self, k) < 0:
        raise ValueError('{} cannot be negative'.format(k))

  def __str__(self) -> str:
    parts = ['P']
    for value, char in [(self.years, 'Y'), (self.months, 'M'), (self.weeks, 'W'), (self.days, 'D')]:
      if value != 0:
        parts.append('{}{}'.format(value, char))
    has_t = False
    for value, char in [(self.hours, 'H'), (self.minutes, 'M'), (self.seconds, 'S')]:
      if value != 0:
        if not has_t:
          parts.append('T')
          has_t = True
        parts.append('{}{}'.format(value, char))
    return ''.join(parts)

  def __repr__(self) -> str:
    return 'Duration({})'.format(', '.join('{}={}'.format(k, getattr(self, k)) for k in self._fields))

  def __eq__(self, other) -> bool:
    if type(other) != type(self):
      return False
    for k in self._fields:
      if getattr(self, k) != getattr(other, k):
        return False
    return True

  def __ne__(self, other) -> bool:
    if type(other) != type(self):
      return True
    for k in self._fields:
      if getattr(self, k) == getattr(other, k):
        return False
    return True

  def total_seconds(self, days_per_month: int = 31, days_per_year: float = 365.25) -> int:
    """
    Computes the total number of seconds in this duration.
    """

    seconds_per_day = 3600 * 24
    return (
      int(self.years * days_per_year * seconds_per_day) +
      int(self.months * days_per_month * seconds_per_day) +
      self.weeks * 7 * seconds_per_day +
      self.days * seconds_per_day +
      self.hours * 3600 +
      self.minutes * 60 +
      self.seconds)

  def as_timedelta(self, *args, **kwargs) -> timedelta:
    """
    Returns the seconds represented by this duration as a #timedelta object. The arguments
    and keyword arguments are forwarded to the #total_seconds() method.
    """

    return timedelta(seconds=self.total_seconds(*args, **kwargs))

  def as_relativedelta(self) -> 'dateutil.relativedelta.relativedelta':
    """
    Converts the #Duration object to a #dateutil.relativedelta.relativedelta object. Requires
    the `python-dateutil` module.
    """

    from dateutil.relativedelta import relativedelta
    return relativedelta(years=self.years, months=self.months, weeks=self.weeks, days=self.days,
                         hours=self.hours, minutes=self.minutes, seconds=self.seconds)

  @classmethod
  def parse(cls, s: str) -> 'Duration':
    """
    Parses an ISO 8601 duration string into a #Duration object.

    Thanks to https://stackoverflow.com/a/35936407.
    See also https://en.wikipedia.org/wiki/ISO_8601#Durations
    """

    parts = s.split('T')
    if not s or s[0] != 'P' or len(parts) > 2:
      raise ValueError('Not an ISO 8601 duration string: {!r}'.format(s))

    part_one = parts[0][1:]
    part_two = parts[1] if len(parts) == 2 else ''

    fields = {}

    try:
      for number, unit in (x.groups() for x in match_all(r'(\d+)(D|W|M|Y)', part_one)):
        number = int(number)
        if unit == 'Y':
          fields['years'] = number
        elif unit == 'M':
          fields['months'] = number
        elif unit == 'W':
          fields['weeks'] = number
        elif unit == 'D':
          fields['days'] = number

      for number, unit in (x.groups() for x in match_all(r'(\d+)(S|H|M)', part_two)):
        number = int(number)
        if unit == 'H':
          fields['hours'] = number
        elif unit == 'M':
          fields['minutes'] = number
        elif unit == 'S':
          fields['seconds'] = number

    except match_all.Error:
      raise ValueError('Not an ISO 8601 duration string: {!r}'.format(s))

    return cls(**fields)


class Iso8601(DatetimeFormat):

  _format_set = root_option_set.create_format_set('Iso8601', [
    '%Y-%m-%dT%H:%M:%S(.%f)?%z',  # RFC 3339
    '%Y-%m-%dT%H:%M:%S(.%f)?',    # ISO 8601 extended format
    '%Y%m%dT%H%M%S(.%f)?',        # ISO 8601 basic format
    '%Y%m%d',                     # ISO 8601 basic format, date only
  ])

  def parse(self, string: str) -> datetime:
    return self._format_set.parse(string)

  def format(self, datetime: datetime) -> str:
    return self._format_set.format(datetime)


class JavaOffsetDatetime(DatetimeFormat):

  _standard = root_option_set.create_format_set('JavaOffsetDatetime', [
    '%Y-%m-%dT%H:%M:%S(.%f)?%z',
    '%Y-%m-%dT%H:%M%z',
  ])

  _optional_tz = root_option_set.create_format_set('JavaOffsetDatetime',
    chain(*zip(_standard, [x.string[:-2] for x in _standard])))

  def __init__(self, require_timezone: bool = True) -> None:
    self.require_timezone = require_timezone
    self._format_set = self._standard if require_timezone else self._optional_tz

  def parse(self, string: str) -> datetime:
    return self._format_set.parse(string)

  def format(self, datetime: datetime) -> str:
    return self._format_set.format(datetime)


def create_datetime_format_set(name: str, formats: t.List[DatetimeFormat]) -> DatetimeFormatSet:
  return root_option_set.create_format_set(name, formats)
