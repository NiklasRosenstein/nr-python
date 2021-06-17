
import datetime
import pandas as pd
from nr.parsing.date.duration import duration

# NOTE(NiklasRosenstein): Some formats below are commented out because they are not supported
#   by the stdlib strptime() (specifically the `+hh` and `-hh` timezone format), and that breaks
#   our benchmarks.

SAMPLES = pd.DataFrame([

  {
    'description': 'ISO-8601 with timezone (UTC)',
    'formatted': [
      '20210317T000000Z',
      '2021-03-17T00:00:00Z',
      #'2021-03-17T00:00:00+00',
      '2021-03-17T00:00:00+0000',
      '2021-03-17T00:00:00.000Z',
      #'2021-03-17T00:00:00.000+00',
      '2021-03-17T00:00:00.000+0000',
    ],
    'fullformat': '2021-03-17T00:00:00.0Z',
    'parsed': datetime.datetime(2021, 3, 17, 0, 0, 0, 0, datetime.timezone.utc),
    'tags': ['iso8601'],
  },
  {
    'description': 'ISO-8601 without timezone',
    'formatted': [
      '20210317',
      '20210317T000000',
      '2021-03-17T00:00:00',
      '2021-03-17T00:00:00.000'
    ],
    'fullformat': '2021-03-17T00:00:00.0',
    'parsed': datetime.datetime(2021, 3, 17, 0, 0, 0, 0),
    'tags': ['iso8601'],
  },
  {
    'description': 'ISO-8601 with timezone (+0100)',
    'formatted': [
      #'2021-04-23T10:24:10+01',
      '2021-04-23T10:24:10+0100',
      '2021-04-23T10:24:10+01:00',
      #'20210423T102410+01',
      '20210423T102410+0100',
      '20210423T102410+01:00',
    ],
    'fullformat': '2021-04-23T10:24:10.0+01:00',
    'parsed': datetime.datetime(2021, 4, 23, 10, 24, 10, 0, datetime.timezone(datetime.timedelta(seconds=3600))),
    'tags': ['iso8601'],
  },
  {
    'description': 'ISO-8601 with sub-seconds',
    'formatted': [
      '2021-04-23T10:24:10.213',
      '2021-04-23T10:24:10.2130',
      '2021-04-23T10:24:10.213000',
    ],
    'fullformat': '2021-04-23T10:24:10.213',
    'parsed': datetime.datetime(2021, 4, 23, 10, 24, 10, 213000),
    'tags': ['iso8601'],
  },

  {
    'description': 'ISO-8601 duration',
    'formatted': ['P30D'],
    'fullformat': 'P30D',
    'parsed': duration(days=30),
    'tags': ['iso8601']
  },
  {
    'description': 'ISO-8601 duration',
    'formatted': ['P1DT5M'],
    'fullformat': 'P1DT5M',
    'parsed': duration(days=1, minutes=5),
    'tags': ['iso8601']
  },
  {
    'description': 'ISO-8601 duration',
    'formatted': ['P2Y3M50W23DT3H40M15S'],
    'fullformat': 'P2Y3M50W23DT3H40M15S',
    'parsed': duration(2, 3, 50, 23, 3, 40, 15),
    'tags': ['iso8601']
  },

])

SAMPLES: pd.DataFrame = SAMPLES.explode('formatted')  # type: ignore
