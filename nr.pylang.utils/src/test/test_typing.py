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

from nr.pylang.utils.typing import is_generic, get_generic_args, extract_optional
from typing import Dict, List, Optional, Union


def test_is_generic():
  assert is_generic(List[str])
  assert not is_generic(str)
  assert is_generic(List[str], List)
  assert is_generic(List[str], (Dict, List))
  assert is_generic(List, List)
  assert not is_generic(List, Dict)
  assert not is_generic(List[str], Dict)

  assert is_generic(Union)
  assert is_generic(Union, Union)
  assert not is_generic(Union, Dict)
  assert is_generic(Union[int, str], Union)

  assert is_generic(Optional[List[str]])
  assert is_generic(Optional[List[str]], Optional)
  assert get_generic_args(Optional[List[str]]) == (List[str],)


def test_get_generic_args():
  assert get_generic_args(List) == List.__parameters__
  assert get_generic_args(List[str]) == (str,)


def test_extract_optional():
  assert extract_optional(Optional[List[str]]) == List[str]
  assert extract_optional(Union[List[str], None]) == List[str]
  assert extract_optional(Union[List[str], str]) is None
