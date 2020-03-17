
from dateutil.parser import parse as dateutil_parse
from nr.parsing.date import JavaOffsetDatetime, timezone
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
