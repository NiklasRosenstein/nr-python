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

from nr.types.structured import *
from nr.types.structured.utils.yaml import load as load_yaml_with_metadata


def test_add_origin_metadata_field():

  @utils.add_origin_metadata_field()
  class Item(Object):
    name = Field(str)

  class Config(Object):
    items = Field([Item])

  yaml_data = '''
    items:
      - name: foo
      - name: bar
      - name: baz
  '''

  data = load_yaml_with_metadata(yaml_data, filename='foobar.yaml')
  obj = extract(data, Config)

  assert obj.items[0].origin.filename == 'foobar.yaml'
  assert obj.items[1].origin.filename == 'foobar.yaml'
  assert obj.items[2].origin.filename == 'foobar.yaml'

  assert obj.items[0].origin.lineno == 3
  assert obj.items[1].origin.lineno == 4
  assert obj.items[2].origin.lineno == 5
