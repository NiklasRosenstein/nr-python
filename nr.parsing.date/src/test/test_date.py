
from dateutil.tz import tzutc as dateutil_tzutc
from dateutil.parser import parse as dateutil_parse
from nr.parsing.date import JavaOffsetDatetime, Iso8601, Duration, timezone
import datetime
import pytest


def test_java_offset_datetime_formatting():
  test_cases = [
    ('2019-03-12T10:22-0400',     '2019-03-12T10:22:00.0-04:00'),
    ('2019-03-12T10:22-04:00',    '2019-03-12T10:22:00.0-04:00'),
    ('2019-03-12T10:22:00Z',      '2019-03-12T10:22:00.0Z'),
    ('2019-03-12T10:22:00.4312Z', '2019-03-12T10:22:00.4312Z'),
    ('2019-03-12T10:22:00.0Z',    '2019-03-12T10:22:00.0Z'),
  ]

  def _run_tests(tests, dateformat):
    for sample, formatted in test_cases:
      date = dateformat.parse(sample)
      assert date == dateutil_parse(sample)
      assert dateformat.format(date) == formatted

  _run_tests(test_cases, JavaOffsetDatetime())
  _run_tests(test_cases, JavaOffsetDatetime(require_timezone=False))


def test_java_offset_datetime_timezone():
  dt = JavaOffsetDatetime().parse('2020-04-01T03:12:00Z')
  assert dt.tzinfo == timezone.utc

  with pytest.raises(ValueError) as excinfo:
    JavaOffsetDatetime().parse('2020-04-01T03:12:00')
  assert 'does not match any of the \'JavaOffsetDatetime\' formats.' in str(excinfo.value)

  dt = JavaOffsetDatetime(require_timezone=False).parse('2020-04-01T03:12:00')
  assert dt.tzinfo is None

  with pytest.raises(ValueError) as excinfo:
    JavaOffsetDatetime().format(dt)
  assert 'Date "2020-04-01 03:12:00" cannot be formatted with any of the \'JavaOffsetDatetime\' formats.' in str(excinfo.value)

  assert JavaOffsetDatetime(require_timezone=False).format(dt) == '2020-04-01T03:12:00.0'


def test_iso8601():
  test_cases = [
    ('2020-06-29T07:41:59.000073', datetime.datetime(2020, 6, 29, 7, 41, 59, 73)),
    ('2020-06-29T07:41:59.73', datetime.datetime(2020, 6, 29, 7, 41, 59, 730000)),
    ('2020-06-29T07:41:59.73247Z', datetime.datetime(2020, 6, 29, 7, 41, 59, 732470, timezone.utc)),
  ]
  for sample, result in test_cases:
    assert Iso8601().parse(sample) == result
    assert dateutil_parse(sample) == result
    assert Iso8601().format(result) == sample


def test_iso8601_duration():
  assert Duration.parse('P30D').total_seconds() == datetime.timedelta(days=30).total_seconds()
  assert Duration.parse('P1DT5M').total_seconds() == datetime.timedelta(days=1, minutes=5).total_seconds()
  assert Duration.parse('P5M1D').total_seconds() == datetime.timedelta(days=1 + 5*31).total_seconds()
  assert Duration.parse('PT1S').total_seconds() == 1

  with pytest.raises(ValueError):
    Duration.parse('P5DT1Y')
  with pytest.raises(ValueError):
    Duration.parse('P5D10S')
  with pytest.raises(ValueError):
    Duration.parse('P1S')

  s = 'P2Y3M50W23DT3H40M15S'
  d = Duration(2, 3, 50, 23, 3, 40, 15)
  assert Duration.parse(s) == d
  assert str(d) == s

  assert str(Duration(days=5, minutes=3)) == 'P5DT3M'
  assert str(Duration(minutes=3)) == 'PT3M'
