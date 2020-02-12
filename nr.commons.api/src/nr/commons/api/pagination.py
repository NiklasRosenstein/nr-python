# -*- coding: utf8 -*-
# The MIT License (MIT)
#
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
""" Provides a simple #PaginatedList class. """

__all__ = ['PaginatedList', 'Page']


class PaginatedList(object):

  def __init__(self, get, init_token=None):
    self._get = get
    self._init_token = init_token
    self._page = None

  def __getitem__(self, key):
    return self.page.metadata[key]

  def __iter__(self):
    if self._page is None:
      self._page = self._get_next_page()
    while True:
      for item in self._page:
        yield item
      if self._page._next_page_token is None:
        break
      self._page = self._get_next_page()

  def _get_next_page(self):
    return self._get(self._page._next_page_token
      if self._page else self._init_token)

  @property
  def page(self):
    if self._page is None:
      self._page = self._get_next_page()
    return self._page


class Page(object):

  def __init__(self, items, next_page_token, metadata=None):
    self._items = items
    self._next_page_token = next_page_token
    self._metadata = metadata

  def __len__(self):
    return len(self._items)

  def __getitem__(self, index):
    return self._items[index]

  def __iter__(self):
    return iter(self._items)

  @property
  def items(self):
    return self._items

  @property
  def next_page_token(self):
    return self._next_page_token

  @property
  def metadata(self):
    return self._metadata
