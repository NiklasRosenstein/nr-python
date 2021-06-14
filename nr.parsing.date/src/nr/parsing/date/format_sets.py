
import datetime
import typing as t
from dataclasses import dataclass, field

from nr.parsing.date.format_options import Component
from .format import _datetime_format, date_format, datetime_format, time_format


def _formulate_parse_error(name: str, formats: t.Sequence[_datetime_format], s: str) -> ValueError:
  return ValueError(f'"{s}" does not match {name} date formats ({len(formats)}):' +
    ''.join(f'\n  | {x.format_str}' for x in formats))


@dataclass
class format_set:
  name: str
  reference_url: str
  date_formats: t.List[date_format] = field(default_factory=list)
  datetime_formats: t.List[datetime_format] = field(default_factory=list)
  time_formats: t.List[time_format] = field(default_factory=list)

  def parse_date(self, s: str) -> datetime.date:
    if not self.date_formats:
      raise ValueError(f'{self.name} has no date formats')
    for fmt in self.date_formats:
      try:
        return fmt.parse_date(s)
      except ValueError:
        pass
    raise _formulate_parse_error(self.name, self.date_formats, s)

  def format_date(self, d: datetime.date) -> str:
    if not self.date_formats:
      raise ValueError(f'{self.name} has no date formats')
    return self.date_formats[0].format_date(d)

  def parse_datetime(self, s: str) -> datetime.datetime:
    if not self.datetime_formats:
      raise ValueError(f'{self.name} has no datetime formats')
    for fmt in self.datetime_formats:
      try:
        return fmt.parse_datetime(s)
      except ValueError:
        pass
    raise _formulate_parse_error(self.name, self.datetime_formats, s)

  def format_datetime(self, dt: datetime.datetime) -> str:
    if not self.datetime_formats:
      raise ValueError(f'{self.name} has no datetime formats')
    fmt = next(x for x in self.datetime_formats if bool(x.has_component(Component.Timezone)) == bool(dt.tzinfo))
    return fmt.format_datetime(dt)

  def parse_time(self, s: str) -> datetime.time:
    if not self.time_formats:
      raise ValueError(f'{self.name} has no time formats')
    for fmt in self.time_formats:
      try:
        return fmt.parse_time(s)
      except ValueError:
        pass
    raise _formulate_parse_error(self.name, self.time_formats, s)

  def format_time(self, t: datetime.time) -> str:
    if not self.time_formats:
      raise ValueError(f'{self.name} has no time formats')
    fmt = next(x for x in self.time_formats if bool(x.has_component(Component.Timezone)) == bool(t.tzinfo))
    return fmt.format_time(t)


JAVA_OFFSET_DATETIME = format_set(
  name='Java OffsetDateTime',
  reference_url='https://docs.oracle.com/javase/8/docs/api/java/time/OffsetDateTime.html#toString--',
  datetime_formats=[
    datetime_format.compile('%Y-%m-%dT%H:%M:%S.%f%z'),
    datetime_format.compile('%Y-%m-%dT%H:%M:%S.%f'),
    datetime_format.compile('%Y-%m-%dT%H:%M:%S%z'),
    datetime_format.compile('%Y-%m-%dT%H:%M:%S'),
    datetime_format.compile('%Y-%m-%dT%H:%M%z'),
    datetime_format.compile('%Y-%m-%dT%H:%M'),
  ]
)

ISO_8601 = format_set(
  name='ISO 8061',
  reference_url='https://en.wikipedia.org/wiki/ISO_8601',
  date_formats=[
    date_format.compile('%Y%m%d')
  ],
  datetime_formats=[
    # RFC 3339
    datetime_format.compile('%Y-%m-%dT%H:%M:%S.%f%z'),
    datetime_format.compile('%Y-%m-%dT%H:%M:%S%z'),
    # ISO 8601 extended format
    datetime_format.compile('%Y-%m-%dT%H:%M:%S.%f'),
    datetime_format.compile('%Y-%m-%dT%H:%M:%S'),
    # ISO 8601 basic format
    datetime_format.compile('%Y%m%dT%H%M%S.%f'),
    datetime_format.compile('%Y%m%dT%H%M%S'),
    datetime_format.compile('%Y%m%dT%H%M%S.%f%z'),
    datetime_format.compile('%Y%m%dT%H%M%S%z'),
  ]
)
