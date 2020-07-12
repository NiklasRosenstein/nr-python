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

from .transform import Transformer, Substitution, ValueTransformer
from pytest import raises


def test_basic_transformer():
  def _my_value_transformer(val):
    if isinstance(val, int):
      return val * 10
    return val

  tf = Transformer()
  tf.register_func(_my_value_transformer)

  assert tf.transform(2) == 20
  assert tf.transform(['1', 3]) == ['1', 30]
  assert tf.transform({'a': 13, 'b': [42, "foo"]}) == {'a': 130, 'b': [420, "foo"]}


def test_substitution_transformer():
  vars=  {'items': [{'value': 'foo'}, {'value': 'bar'}]}
  tf = Transformer(Substitution().with_vars(vars))

  payload = {
    'a': '{{items[0].value}}|{{items[1].value}}',
    'b': '{{items[1].value}}',
    'c': '{{items[*].value}}',
  }
  assert tf(payload) == {'a': 'foo|bar', 'b': 'bar', 'c': ['foo', 'bar']}

  payload = {'a': '{{items[0]}}'}
  assert tf(payload) == {'a': {'value': 'foo'}}

  payload = {'a': 'embedded in {{items[0]}} string'}
  with raises(Substitution.Error):
    assert tf(payload)

  payload = {'a': 'embedded in {{items[0].value}} string'}
  assert tf(payload) == {'a': 'embedded in foo string'}


def test_substitution_parallel_transformer():
  a = {'a': {'b': 'foo'}}

  tf = Transformer(Substitution().with_vars(a, relative=True))

  assert tf({'a': {}, 'b': '{{a}}'}) == {'a': {}, 'b': a['a']}
  assert tf({'a': 'spam/{{a.b}}/egg'}) == {'a': 'spam/foo/egg'}

  with raises(Substitution.Error):
    tf({'a': 'spam/{{a}}/egg'})
