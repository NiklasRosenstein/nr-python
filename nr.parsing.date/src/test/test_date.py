
from dateutil.tz import tzutc as dateutil_tzutc
from dateutil.parser import parse as dateutil_parse
from nr.parsing.date import JAVA_OFFSET_DATETIME, ISO_8601, duration
from nr.parsing.date.duration import DAYS_PER_MONTH
import datetime
from datetime import timezone
import pytest

# TODO(NiklasRosenstein): Add time parsing tests


def test_java_offset_datetime_formatting():
  test_cases = [
    # sample,                         formatted
    ('2021-03-17T00:00:00+0000',      '2021-03-17T00:00:00.0Z'),
    ('2019-03-12T10:22-0400',         '2019-03-12T10:22:00.0-04:00'),
    ('2019-03-12T10:22-04:00',        '2019-03-12T10:22:00.0-04:00'),
    ('2019-03-12T10:22:00Z',          '2019-03-12T10:22:00.0Z'),
    ('2019-03-12T10:22:00.4312Z',     '2019-03-12T10:22:00.4312Z'),
    ('2019-03-12T10:22:00.0Z',        '2019-03-12T10:22:00.0Z'),
    ('2021-01-25T09:13:01.180932Z',   '2021-01-25T09:13:01.180932Z'),
    # Nanosecond precision truncated to microsecond.
    ('2021-01-25T09:13:01.180932753Z', '2021-01-25T09:13:01.180932Z'),
  ]

  for sample, formatted in test_cases:
    date = JAVA_OFFSET_DATETIME.parse_datetime(sample)
    assert date == dateutil_parse(sample)
    assert JAVA_OFFSET_DATETIME.format_datetime(date) == formatted


def test_java_offset_datetime_timezone():
  dt = JAVA_OFFSET_DATETIME.parse_datetime('2020-04-01T03:12:00Z')
  assert dt == datetime.datetime(2020, 4, 1, 3, 12, tzinfo=timezone.utc)
  assert JAVA_OFFSET_DATETIME.format_datetime(dt) == '2020-04-01T03:12:00.0Z'

  dt = JAVA_OFFSET_DATETIME.parse_datetime('2020-04-01T03:12:00')
  assert dt == datetime.datetime(2020, 4, 1, 3, 12)
  assert JAVA_OFFSET_DATETIME.format_datetime(dt) == '2020-04-01T03:12:00.0'


def test_iso8601():
  test_cases = [
    ('2021-03-17T00:00:00+0000', datetime.datetime(2021, 3, 17, 0, 0, 0, 0, timezone.utc), '2021-03-17T00:00:00.0Z'),
    ('2020-06-29T07:41:59.000073', datetime.datetime(2020, 6, 29, 7, 41, 59, 73), None),
    ('2020-06-29T07:41:59.73', datetime.datetime(2020, 6, 29, 7, 41, 59, 730000), None),
    ('2020-06-29T07:41:59.73247Z', datetime.datetime(2020, 6, 29, 7, 41, 59, 732470, timezone.utc), None),
  ]
  for sample, result, formatted in test_cases:
    if formatted is None:
      formatted = sample
    assert ISO_8601.parse_datetime(sample) == result
    assert dateutil_parse(sample) == result
    assert ISO_8601.format_datetime(result) == formatted


def test_iso8601_duration():
  assert duration.parse('P30D').total_seconds() == datetime.timedelta(days=30).total_seconds()
  assert duration.parse('P1DT5M').total_seconds() == datetime.timedelta(days=1, minutes=5).total_seconds()
  assert duration.parse('P5M1D').total_seconds() == datetime.timedelta(days=1 + 5*DAYS_PER_MONTH).total_seconds()
  assert duration.parse('PT1S').total_seconds() == 1

  with pytest.raises(ValueError):
    duration.parse('P5DT1Y')
  with pytest.raises(ValueError):
    duration.parse('P5D10S')
  with pytest.raises(ValueError):
    duration.parse('P1S')

  s = 'P2Y3M50W23DT3H40M15S'
  d = duration(2, 3, 50, 23, 3, 40, 15)
  assert duration.parse(s) == d
  assert str(d) == s

  assert str(duration(days=5, minutes=3)) == 'P5DT3M'
  assert str(duration(minutes=3)) == 'PT3M'
