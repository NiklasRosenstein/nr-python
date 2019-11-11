
from dateutil.parser import parse as dateutil_parse
from nr.parsing.date import JAVA_OFFSET_DATETIME

DATES_TO_TEST = [
    ('2019-03-12T10:22-0400',     '2019-03-12T10:22:00.0-04:00'),
    ('2019-03-12T10:22-04:00',    '2019-03-12T10:22:00.0-04:00'),
    ('2019-03-12T10:22:00Z',      '2019-03-12T10:22:00.0Z'),
    ('2019-03-12T10:22:00.4312Z', '2019-03-12T10:22:00.4312Z'),
    ('2019-03-12T10:22:00.0Z',    '2019-03-12T10:22:00.0Z'),
]


def test_parse_date():
  for sample, formatted in DATES_TO_TEST:
    date = JAVA_OFFSET_DATETIME.parse(sample)
    assert date == dateutil_parse(sample)
    assert JAVA_OFFSET_DATETIME.format(date) == formatted
