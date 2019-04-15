
import pytest
import types

from numbers import Number
from nr.types import stream


def test_getitem():
  assert list(stream(range(10))[3:8]) == [3, 4, 5, 6, 7]


def test_call():
  funcs = [(lambda x: x*2), (lambda x: x+2), (lambda x: x//2)]
  assert list(stream.call(funcs, 3)) == [6, 5, 1]


def test_map():
  values = [5, 2, 1]
  assert list(stream.map(values, lambda x: x*2)) == [10, 4, 2]


def test_flatmap():
  values = ['abc', 'def']
  assert ''.join(stream.flatmap(values, lambda x: x)) == 'abcdef'


def test_filter():
  assert list(stream.filter(range(10), lambda x: x % 2 == 0)) == [0, 2, 4, 6, 8]


def test_unique():
  values = [1, 5, 6, 5, 3, 8, 1, 3, 9, 0]
  assert list(stream.unique(values)) == [1, 5, 6, 3, 8, 9, 0]


def test_chunks():
  values = [3, 6, 4, 7, 1, 2, 5]
  assert list(stream.chunks(values, 3, 0).map(sum)) == [13, 10, 5]


def test_concat():
  values = ['abc', 'def']
  assert ''.join(stream.concat(values)) == 'abcdef'


def test_chain():
  values = ['abc', 'def']
  assert ''.join(stream.chain(*values)) == 'abcdef'


def test_attr():
  values = [{'foo': 'bar', 'spam': 'cheese'}, {'bam': 'baz'}]
  assert sorted(stream.attr(values, 'keys').call().concat()) == ['bam', 'foo', 'spam']
  assert sorted(stream.attr(values, 'values').call().concat()) == ['bar', 'baz', 'cheese']


def test_item():
  values = [{'foo': 'bar', 'spam': 'cheese'}, {'bam': 'baz'}]
  assert list(stream.item(values, 'foo', None)) == ['bar', None]
  with pytest.raises(KeyError):
    list(stream.item(values, 'foo'))


def test_of_type():
  values = [0, object(), 'foo', 42.0]
  assert list(stream.of_type(values, int)) == [0]
  assert list(stream.of_type(values, object)) == values
  assert list(stream.of_type(values, str)) == ['foo']
  assert list(stream.of_type(values, float)) == [42.0]
  assert list(stream.of_type(values, Number)) == [0, 42.0]


def test_partition():
  odd, even = stream.partition(range(10), lambda x: x % 2 == 0)
  assert list(odd) == [1, 3, 5, 7, 9]
  assert list(even) == [0, 2, 4, 6, 8]


def test_dropwhile():
  values = list(stream.chain(range(5), range(8, 2, -1)))
  assert list(values) == [0, 1, 2, 3, 4, 8, 7, 6, 5, 4, 3]
  assert list(stream.dropwhile(values, lambda x: x < 4)) == [4, 8, 7, 6, 5, 4, 3]


def test_takewhile():
  values = list(stream.chain(range(5), range(8, 2, -1)))
  assert list(values) == [0, 1, 2, 3, 4, 8, 7, 6, 5, 4, 3]
  assert list(stream.takewhile(values, lambda x: x < 8)) == [0, 1, 2, 3, 4]
  assert list(stream.takewhile(values, lambda x: x > 0)) == []


def test_groupby():
  companies = [
    {'country': 'India', 'company': 'Flipkart'},
    {'country': 'India', 'company': 'Myntra'},
    {'country': 'India', 'company': 'Paytm'},
    {'country': 'USA', 'company': 'Apple'},
    {'country': 'USA', 'company': 'Facebook'},
    {'country': 'Japan', 'company': 'Canon'},
    {'country': 'Japan', 'company': 'Pixela'}]

  by_country = stream.groupby(companies, key=lambda x: x['country'])\
                     .map(lambda x: (x[0], list(x[1])))\
                     .collect()

  countries = stream(by_country).map(lambda x: x[0]).collect(sorted)
  assert countries == ['India', 'Japan', 'USA']

  companies = stream(by_country).map(lambda x: (x[0], stream.map(x[1], lambda x: x['company']).collect(sorted)))\
                                .collect(sorted, key=lambda x: x[0])
  assert companies == [('India', ['Flipkart', 'Myntra', 'Paytm']), ('Japan', ['Canon', 'Pixela']), ('USA', ['Apple', 'Facebook'])]


def test_slice():
  assert list(stream.slice(range(10), 3, 8)) == [3, 4, 5, 6, 7]


def test_next():
  values = [4, 2, 1]
  assert stream.next(values) == 4


def test_length():
  values = [4, 2, 7]
  assert stream.flatmap(values, lambda x: ' '*x).length() == sum(values)


def test_consume():
  s = stream(range(10))
  assert list(s) == list(range(10))
  s = stream(range(10)).consume()
  assert list(s) == []
  s = stream(range(10)).consume(5)
  assert list(s) == list(range(5, 10))


def test_collect():
  values = [4, 8, 2, 7, 4]
  assert stream(values).map(lambda x: x-2).collect() == [2, 6, 0, 5, 2]
  assert stream(values).map(lambda x: x-2).collect(sorted) == [0, 2, 2, 5, 6]
  assert stream(values).map(lambda x: x-2).collect(set) == set([0, 2, 5, 6])
