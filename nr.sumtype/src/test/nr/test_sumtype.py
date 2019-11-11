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

from nr.sumtype import Constructor, Sumtype, add_constructor_tests
import collections


def test_sumtype_inheritance():

  @add_constructor_tests
  class Result(Sumtype):
    Loading = Constructor('progress')
    Error = Constructor('message')

    @Constructor
    class Ok(collections.namedtuple('Ok', 'filename,load')):
      def say_ok(self):
        return 'Ok! ' + self.load()

    @Loading.member
    def alert(self):
      return 'Progress: ' + str(self.progress)

    Error.add_member('static_error_member', "This is a member on Error!")

  assert not hasattr(Result, 'alert')
  assert not hasattr(Result, 'static_error_member')

  x = Result.Loading(0.5)
  assert isinstance(x, Result)
  assert x.is_loading()
  assert not x.is_error()
  assert not x.is_ok()
  assert hasattr(x, 'alert')
  assert not hasattr(x, 'static_error_member')
  assert x.alert() == 'Progress: 0.5'
  assert x.progress == 0.5

  @add_constructor_tests
  class MoreResult(Result):
    InvalidState = Constructor()

  assert MoreResult.Loading is not Result.Loading
  assert MoreResult.Error is not Result.Error
  assert MoreResult.Ok is not Result.Ok

  x = MoreResult.Loading(0.5)
  assert isinstance(x, Result)
  assert x.is_loading()
  assert not x.is_error()
  assert not x.is_ok()
  assert hasattr(x, 'alert')
  assert not hasattr(x, 'static_error_member')
  assert x.alert() == 'Progress: 0.5'
  assert x.progress == 0.5
  assert isinstance(x, MoreResult)
  assert not hasattr(x, 'say_ok')

  x = MoreResult.InvalidState()
  assert x.is_invalid_state()
  assert isinstance(x, MoreResult)
  assert not hasattr(x, 'say_ok')

  ok = MoreResult.Ok('/tmp/test.txt', lambda: 'Hello')
  assert hasattr(ok, 'say_ok')
  assert ok.say_ok() == 'Ok! Hello'


def test_sumtype_default():

  class MySumtype(Sumtype):
    A = Constructor('a')
    B = Constructor('b,c')
    __default__ = A

  assert type(MySumtype(42)) is MySumtype.A
  assert MySumtype(42).a == 42

  assert type(MySumtype.B(1, 2)) is MySumtype.B
  assert MySumtype.B(1, 2) == MySumtype.B(1, 2)
  assert MySumtype.B(1, 2).c == 2
