
import pytest
import typing as t

from numbers import Number
from nr.stream import Stream


def test_stream_module_members():
  assert Stream([1, 2, 3]).flatmap(lambda x: [x, x+1]).collect() == [1, 2, 2, 3, 3, 4]


def test_getitem():
  assert list(Stream(range(10))[3:8]) == [3, 4, 5, 6, 7]


def test_call():
  funcs = [(lambda x: x*2), (lambda x: x+2), (lambda x: x//2)]
  assert list(Stream(funcs).call(3)) == [6, 5, 1]


def test_map():
  values = [5, 2, 1]
  assert list(Stream(values).map(lambda x: x*2)) == [10, 4, 2]


def test_flatmap():
  values = ['abc', 'def']
  assert ''.join(Stream(values).flatmap(lambda x: x)) == 'abcdef'


def test_filter():
  assert list(Stream(range(10)).filter(lambda x: x % 2 == 0)) == [0, 2, 4, 6, 8]


def test_distinct():
  values = [1, 5, 6, 5, 3, 8, 1, 3, 9, 0]
  assert list(Stream(values).distinct()) == [1, 5, 6, 3, 8, 9, 0]
  assert list(Stream(values).distinct(skip=set([5, 3, 9]))) == [1, 6, 8, 0]


def test_concat() -> None:
  values = ['abc', 'def']
  s1: Stream[str] = Stream(values).concat()
  assert ''.join(s1) == 'abcdef'

  s2: Stream[str] = Stream([values, values]).concat()
  assert s2.collect() == (values + values)


def test_of_type():
  values = [0, object(), 'foo', 42.0]
  assert list(Stream(values).of_type(int)) == [0]
  assert list(Stream(values).of_type(object)) == values
  assert list(Stream(values).of_type(str)) == ['foo']
  assert list(Stream(values).of_type(float)) == [42.0]
  assert list(Stream(values).of_type(Number)) == [0, 42.0]


def test_bipartition():
  odd, even = Stream(range(10)).bipartition(lambda x: x % 2 == 0)
  assert list(odd) == [1, 3, 5, 7, 9]
  assert list(even) == [0, 2, 4, 6, 8]


def test_dropwhile():
  values = list(Stream(range(5)).append(range(8, 2, -1)))
  assert list(values) == [0, 1, 2, 3, 4, 8, 7, 6, 5, 4, 3]
  assert list(Stream(values).dropwhile(lambda x: x < 4)) == [4, 8, 7, 6, 5, 4, 3]


def test_takewhile():
  values = list(Stream(range(5)).append(range(8, 2, -1)))
  assert list(values) == [0, 1, 2, 3, 4, 8, 7, 6, 5, 4, 3]
  assert list(Stream(values).takewhile(lambda x: x < 8)) == [0, 1, 2, 3, 4]
  assert list(Stream(values).takewhile(lambda x: x > 0)) == []


def test_groupby():
  companies = [
    {'country': 'India', 'company': 'Flipkart'},
    {'country': 'India', 'company': 'Myntra'},
    {'country': 'India', 'company': 'Paytm'},
    {'country': 'USA', 'company': 'Apple'},
    {'country': 'USA', 'company': 'Facebook'},
    {'country': 'Japan', 'company': 'Canon'},
    {'country': 'Japan', 'company': 'Pixela'}]

  by_country = Stream(companies).groupby(key=lambda x: x['country'])\
                     .map(lambda x: (x[0], list(x[1])))\
                     .collect()

  countries = Stream(by_country).map(lambda x: x[0]).collect(lambda x: sorted(x))
  assert countries == ['India', 'Japan', 'USA']

  comp = (Stream(by_country)
      .map(lambda x: (x[0], Stream(x[1]).map(lambda x: x['company']).collect(lambda x: sorted(x))))
      .collect(lambda x: sorted(x, key=lambda x: x[0])))
  assert comp == [
    ('India', ['Flipkart', 'Myntra', 'Paytm']),
    ('Japan', ['Canon', 'Pixela']),
    ('USA', ['Apple', 'Facebook'])]


def test_groupby_2_with_types() -> None:
  entries = [
    ('fix', 'general', 'Fixed this'),
    ('fix', 'packaging', 'Fixed packaging'),
    ('change', 'general', 'Changed that'),
  ]

  result: Stream[t.Tuple[str, t.List[t.Tuple[str, str, str]]]] = (Stream(entries)
      .sortby(lambda x: x[1])
      .groupby(lambda x: x[1], lambda it: list(it)))
  assert list(result) == [
    ('general', [entries[0], entries[2]]),
    ('packaging', [entries[1]])
  ]


def test_slice():
  assert list(Stream(range(10)).slice(3, 8)) == [3, 4, 5, 6, 7]
  assert list(Stream(range(10))[3:8]) == [3, 4, 5, 6, 7]


def test_next():
  values = [4, 2, 1]
  assert Stream(values).next() == 4

  s = Stream(values)
  assert s.next() == 4
  assert s.next() == 2
  assert s.next() == 1
  with pytest.raises(StopIteration):
    s.next()


def test_length():
  values = [4, 2, 7]
  assert Stream(values).flatmap(lambda x: ' '*x).count() == sum(values)


def test_consume():
  s = Stream(range(10))
  assert list(s) == list(range(10))
  s = Stream(range(10)).consume()
  assert list(s) == []
  s = Stream(range(10)).consume(5)
  assert list(s) == list(range(5, 10))


def test_collect():
  values = [4, 8, 2, 7, 4]
  assert Stream(values).map(lambda x: x-2).collect() == [2, 6, 0, 5, 2]
  assert Stream(values).map(lambda x: x-2).collect(lambda x: sorted(x)) == [0, 2, 2, 5, 6]
  assert Stream(values).map(lambda x: x-2).collect(lambda x: set(x)) == set([0, 2, 5, 6])


def test_collect_immediate_return():
  values = [1, 2, 3]
  assert Stream(values).collect() is values
  assert Stream(iter(values)).collect() == values
  assert Stream(values).collect(lambda x: list(x)) is not values
  assert Stream(values).collect(lambda x: list(x)) == values


def test_batch():
  batches1 = list(Stream(range(27)).batch(10))
  assert batches1[0] == list(range(10))
  assert batches1[1] == list(range(10, 20))
  assert batches1[2] == list(range(20, 27))

  batches2 = Stream(range(27)).batch(10, lambda x: x)
  assert list(next(batches2)) == list(range(10))
  assert list(next(batches2)) == list(range(10, 20))
  assert list(next(batches2)) == list(range(20, 27))
  with pytest.raises(StopIteration):
    next(batches2)

  assert list(Stream([3, 6, 4, 7, 1, 2, 5]).batch(3).map(sum)) == [13, 10, 5]


def test_sortby():
  class test_class(object):
    a = 99
  values = [{'a': 42}, {'a': 7}, test_class()]
  def get(item):
    if hasattr(item, 'get'):
      return item.get('a')
    else:
      return item.a
  assert Stream(values).sortby('a').map(get).collect() == [7, 42, 99]


def test_sort():
  values = [3, 2, 7]
  assert list(Stream(values).sort()) == [2, 3, 7]
  assert Stream(values).sort().collect() == [2, 3, 7]


def test_reduce():
  values: t.List[t.Dict[str, str]] = [{}, {'foo': 'bar'}, {'spam': 'egg'}]

  def agg(a: t.Dict[str, str], b: t.Dict[str, str]) -> t.Dict[str, str]:
    a.update(b)
    return a
  result = Stream(values).reduce(agg, {'a': 'b'})
  assert result == {'foo': 'bar', 'spam': 'egg', 'a': 'b'}
  assert values[0] == {}

  result = Stream(values).reduce(lambda a, b: (a.update(b), a)[1])
  assert result == {'foo': 'bar', 'spam': 'egg'}
  assert values[0] is result


def test_dropnone():
  assert Stream([None, 42, None, 99]).dropnone().collect() == [42, 99]


def test_first():
  assert Stream([42, 99]).first() == 42
  assert Stream().first() is None
