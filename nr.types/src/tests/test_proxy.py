# -*- coding: utf8 -*-
# Copyright (c) 2019 Niklas Rosenstein
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

from nr.types import abc
from nr.types.proxy import Proxy, proxy_decorator, make_proxy_class


def test_proxy():
    p = Proxy(lambda: None)

    assert p == None

    # An unfortunate behavior, that is why we have the [[make_proxy_class()]]
    # function (see [[test_proxy_iterable()]] below.
    assert isinstance(p, abc.Iterable)

    # TODO(NiklasRosenstein): Why does it not behave like abc.Iterable?
    assert not isinstance(p, abc.Mapping)


def test_proxy_iterable():
    NonIterableProxy = make_proxy_class('NonIterableProxy', exclude=['__iter__'])

    p = NonIterableProxy(lambda: None)
    assert p == None
    assert not hasattr(p, '__iter__')
    assert not hasattr(NonIterableProxy, '__iter__')
    assert not isinstance(p, abc.Mapping)
    assert not isinstance(p, abc.Iterable), NonIterableProxy.__mro__

    NonIterableLazyProxy = make_proxy_class('NonIterableLazyProxy', exclude=['__iter__'])
    @proxy_decorator(NonIterableLazyProxy, lazy=True)
    def p():
        count[0] += 1
        return count[0]

    count = [0]
    assert p == 1
    assert p == 1
    assert p == 1
    assert not hasattr(p, '__iter__')
    assert not hasattr(NonIterableProxy, '__iter__')
    assert not isinstance(p, abc.Mapping)
    assert not isinstance(p, abc.Iterable), NonIterableProxy.__mro__


def test_proxy_auto_increment():
    count = [0]

    @proxy_decorator()
    def auto_increment():
        count[0] += 1
        return count[0]

    assert auto_increment == 1
    assert auto_increment == 2
    assert auto_increment + 10 == 13
    assert count[0] == 3


def test_proxy_lazy_not_auto_increment():
    count = [0]

    @proxy_decorator(lazy=True)
    def not_incrementing():
        count[0] += 1
        return count[0]

    assert not_incrementing == 1
    assert not_incrementing == 1
    assert not_incrementing == 1
    assert count[0] == 1
