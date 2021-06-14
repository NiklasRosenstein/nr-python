
> Note: This package is in the dangerous land of `0.x.y` versions and may be subject to breaking
> changes with minor version increments.

# nr.parsing.date

A fast, regular-expression based library for parsing dates and durations.

__Requirements__

* Python 3.6+

__Supported Date & Time Formats__

- `%Y` &ndash; 4 digit year
- `%m` &ndash; 2 digit month
- `%d` &ndash; 2 digit day
- `%H` &ndash; 2 digit hour
- `%M` &ndash; 2 digit minute
- `%S` &ndash; 2 digit second
- `%f` &ndash; arbitrary precision milliseconds
- `%z` &ndash; timezone offset (`[+-]\d\d:?\d\d` offset or `Z` for UTC)

__Built-in format collections__

* `ISO_8601` (see [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) on Wikipedia)
* `JAVA_OFFSET_DATETIME` (see [OffsetDateTime](https://docs.oracle.com/javase/8/docs/api/java/time/OffsetDateTime.html) class on the Java 8 API documentation)

## Quickstart

```python
from nr.parsing.date import duration, ISO_8601
ISO_8601.parse('2021-04-21T10:13:00.124+0000')
duration.parse('P3Y6M4DT12H30M5S')
```

---

<p align="center">Copyright &copy; 2020 Niklas Rosenstein</p>
