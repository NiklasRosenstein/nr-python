# -*- coding: utf8 -*-
# Copyright (c) 2020 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

from .util import AccessorList, merge_dicts


def test_accessor_list():
  assert AccessorList('a.b[*].c[1]')._items == ['a', 'b', AccessorList.WILDCARD, 'c', 1]

  data = {
    'books': [
      {
        'title': 'Python Coding - Part 1',
        'keywords': ['python', 'software', 'coding', 'tutorial'],
      },
      {
        'title': 'Da Vinci',
        'keywords': ['novel', 'illuminati'],
      },
    ],
  }

  assert AccessorList('books[1].title')(data) == 'Da Vinci'
  assert AccessorList('books[*].title')(data) == ['Python Coding - Part 1', 'Da Vinci']


def test_merge_dicts():
  assert merge_dicts(
    {'a': {'b': 0, 'c': 1}, 'd': [2, 3]},
    {'a': {'c': 42}, 'd': None},
  ) == {'a': {'b': 0, 'c': 42}, 'd': None}
  assert merge_dicts(
    {'a': 'foo'},
    {'a': '{{exclude}}'},
  ) == {}
