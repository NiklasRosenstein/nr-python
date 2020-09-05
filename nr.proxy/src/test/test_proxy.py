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

import threading
from collections import abc
from nr.proxy import *

import pytest


def test_proxy():
    p = proxy(lambda: None)

    assert p == None

    # An unfortunate behavior, that is why we have the #make_cls()
    # function (see #test_proxy_iterable() below.
    assert isinstance(p, abc.Iterable)

    # TODO(NiklasRosenstein): Why does it not behave like abc.Iterable?
    assert not isinstance(p, abc.Mapping)


def test_proxy_iterable():
    NonIterableProxy = make_cls('NonIterableProxy', exclude=['__iter__'])
    print(NonIterableProxy)
    print(NonIterableProxy.__bases__)

    p = NonIterableProxy(lambda: None)
    assert p == None
    assert not hasattr(p, '__iter__')
    assert not hasattr(NonIterableProxy, '__iter__')
    assert not isinstance(p, abc.Mapping)
    assert not isinstance(p, abc.Iterable), NonIterableProxy.__mro__

    NonIterableLazyProxy = make_cls('NonIterableLazyProxy', exclude=['__iter__'])

    def _func():
        count[0] += 1
        return count[0]
    p = NonIterableLazyProxy(_func, lazy=True)

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

    def auto_increment_():
        count[0] += 1
        return count[0]
    auto_increment = proxy(auto_increment_)

    assert auto_increment == 1
    assert auto_increment == 2
    assert auto_increment + 10 == 13
    assert count[0] == 3


def test_proxy_lazy_not_auto_increment():
    count = [0]

    def auto_increment_():
        count[0] += 1
        return count[0]
    auto_increment = proxy(auto_increment_, lazy=True)

    assert auto_increment == 1
    assert auto_increment == 1
    assert auto_increment == 1
    assert count[0] == 1


def test_threadlocal():
    l = threadlocal[int]()
    sink = set()
    lock = threading.Lock()

    def _run(value: int):
        for i in range(1000):
            assert empty(l)
            push(l, value)
            assert not empty(l)
            assert get(l) == value
            assert pop(l) == value
            assert empty(l)
        with lock:
            sink.add(value)

    threads = [
        threading.Thread(target=lambda: _run(99)),
        threading.Thread(target=lambda: _run(10)),
        threading.Thread(target=lambda: _run(321)),
    ]
    [t.start() for t in threads]
    _run(42)
    [t.join() for t in threads]

    assert sink == set([99, 10, 321, 42])
