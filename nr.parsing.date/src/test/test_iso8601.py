
import datetime
import pytest
from nr.parsing.date import ISO_8601, duration
from .samples import SAMPLES

ISO8601_DATETIME_SAMPLES = SAMPLES[SAMPLES.tags.apply(lambda x: 'iso8601' in x) &
  SAMPLES.parsed.apply(lambda x: isinstance(x, datetime.datetime))]

ISO8601_DURATION_SAMPLES = SAMPLES[SAMPLES.tags.apply(lambda x: 'iso8601' in x) &
  SAMPLES.parsed.apply(lambda x: isinstance(x, duration))]


@pytest.mark.parametrize('row', (x[1] for x in ISO8601_DATETIME_SAMPLES.iterrows()))
def test_iso8601_datetime(row):
  assert ISO_8601.parse_datetime(row.formatted, partial=True) == row.parsed
  assert ISO_8601.format_datetime(row.parsed) == row.fullformat


@pytest.mark.parametrize('row', (x[1] for x in ISO8601_DURATION_SAMPLES.iterrows()))
def test_iso8601_duration(row):
  assert duration.parse(row.formatted) == row.parsed
  assert str(row.parsed) == row.fullformat
