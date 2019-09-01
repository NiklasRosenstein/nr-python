
import pytest
import types

from numbers import Number
from nr.types import stream
from nr.types.stream import Stream


def test_stream_module_members():
  assert stream.flatmap([1, 2, 3], lambda x: [x, x+1]).collect() == [1, 2, 2, 3, 3, 4]


def test_getitem():
  assert list(Stream(range(10))[3:8]) == [3, 4, 5, 6, 7]


def test_call():
  funcs = [(lambda x: x*2), (lambda x: x+2), (lambda x: x//2)]
  assert list(Stream.call(funcs, 3)) == [6, 5, 1]


def test_map():
  values = [5, 2, 1]
  assert list(Stream.map(values, lambda x: x*2)) == [10, 4, 2]


def test_flatmap():
  values = ['abc', 'def']
  assert ''.join(Stream.flatmap(values, lambda x: x)) == 'abcdef'


def test_filter():
  assert list(Stream.filter(range(10), lambda x: x % 2 == 0)) == [0, 2, 4, 6, 8]


def test_unique():
  values = [1, 5, 6, 5, 3, 8, 1, 3, 9, 0]
  assert list(Stream.unique(values)) == [1, 5, 6, 3, 8, 9, 0]


def test_chunks():
  values = [3, 6, 4, 7, 1, 2, 5]
  assert list(Stream.chunks(values, 3, 0).map(sum)) == [13, 10, 5]


def test_concat():
  values = ['abc', 'def']
  assert ''.join(Stream.concat(values)) == 'abcdef'


def test_chain():
  values = ['abc', 'def']
  assert ''.join(Stream.chain(*values)) == 'abcdef'


def test_attr():
  values = [{'foo': 'bar', 'spam': 'cheese'}, {'bam': 'baz'}]
  assert sorted(Stream.attr(values, 'keys').call().concat()) == ['bam', 'foo', 'spam']
  assert sorted(Stream.attr(values, 'values').call().concat()) == ['bar', 'baz', 'cheese']


def test_item():
  values = [{'foo': 'bar', 'spam': 'cheese'}, {'bam': 'baz'}]
  assert list(Stream.item(values, 'foo', None)) == ['bar', None]
  with pytest.raises(KeyError):
    list(Stream.item(values, 'foo'))


def test_of_type():
  values = [0, object(), 'foo', 42.0]
  assert list(Stream.of_type(values, int)) == [0]
  assert list(Stream.of_type(values, object)) == values
  assert list(Stream.of_type(values, str)) == ['foo']
  assert list(Stream.of_type(values, float)) == [42.0]
  assert list(Stream.of_type(values, Number)) == [0, 42.0]


def test_partition():
  odd, even = Stream.partition(range(10), lambda x: x % 2 == 0)
  assert list(odd) == [1, 3, 5, 7, 9]
  assert list(even) == [0, 2, 4, 6, 8]


def test_dropwhile():
  values = list(Stream.chain(range(5), range(8, 2, -1)))
  assert list(values) == [0, 1, 2, 3, 4, 8, 7, 6, 5, 4, 3]
  assert list(Stream.dropwhile(values, lambda x: x < 4)) == [4, 8, 7, 6, 5, 4, 3]


def test_takewhile():
  values = list(Stream.chain(range(5), range(8, 2, -1)))
  assert list(values) == [0, 1, 2, 3, 4, 8, 7, 6, 5, 4, 3]
  assert list(Stream.takewhile(values, lambda x: x < 8)) == [0, 1, 2, 3, 4]
  assert list(Stream.takewhile(values, lambda x: x > 0)) == []


def test_groupby():
  companies = [
    {'country': 'India', 'company': 'Flipkart'},
    {'country': 'India', 'company': 'Myntra'},
    {'country': 'India', 'company': 'Paytm'},
    {'country': 'USA', 'company': 'Apple'},
    {'country': 'USA', 'company': 'Facebook'},
    {'country': 'Japan', 'company': 'Canon'},
    {'country': 'Japan', 'company': 'Pixela'}]

  by_country = Stream.groupby(companies, key=lambda x: x['country'])\
                     .map(lambda x: (x[0], list(x[1])))\
                     .collect()

  countries = Stream(by_country).map(lambda x: x[0]).collect(sorted)
  assert countries == ['India', 'Japan', 'USA']

  companies = Stream(by_country).map(lambda x: (x[0], Stream.map(x[1], lambda x: x['company']).collect(sorted)))\
                                .collect(sorted, key=lambda x: x[0])
  assert companies == [('India', ['Flipkart', 'Myntra', 'Paytm']), ('Japan', ['Canon', 'Pixela']), ('USA', ['Apple', 'Facebook'])]


def test_slice():
  assert list(Stream.slice(range(10), 3, 8)) == [3, 4, 5, 6, 7]


def test_next():
  values = [4, 2, 1]
  assert Stream.next(values) == 4

  stream = Stream(values)
  assert stream.next() == 4
  assert stream.next() == 2
  assert stream.next() == 1
  with pytest.raises(StopIteration):
    stream.next()


def test_length():
  values = [4, 2, 7]
  assert Stream.flatmap(values, lambda x: ' '*x).length() == sum(values)


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
  assert Stream(values).map(lambda x: x-2).collect(sorted) == [0, 2, 2, 5, 6]
  assert Stream(values).map(lambda x: x-2).collect(set) == set([0, 2, 5, 6])


def test_collect_immediate_return():
  values = [1, 2, 3]
  assert Stream(values).collect() is values
  assert Stream(iter(values)).collect() == values
  assert Stream(values).collect(list) is not values
  assert Stream(values).collect(list) == values


def test_batch():
  batches = list(Stream.batch(range(27), 10))
  assert batches[0] == list(range(10))
  assert batches[1] == list(range(10, 20))
  assert batches[2] == list(range(20, 27))

  batches = Stream.batch(range(27), 10, lambda x: x)
  assert list(next(batches)) == list(range(10))
  assert list(next(batches)) == list(range(10, 20))
  assert list(next(batches)) == list(range(20, 27))
  with pytest.raises(StopIteration):
    next(batches)


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
