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

import sys
from ..core.adapters import DefaultTypeMapper

default_type_mapper = None
module_type_mappers = {}


def set_type_mapper(module, mapper):  # type: (str, ITypeMapper)
  """ Sets the type mapper for a module. """

  module_type_mappers[module] = mapper


def set_default_type_mapper(mapper):  # type: ()
  """ Sets the default type mapper. """

  global default_type_mapper
  default_type_mapper = mapper


def get_type_mapper(module=None, _stackdepth=0):  # type: (Optional[str], int) -> ITypeMapper
  """ Retrieves the type mapper for the specified *module*. If no module is
  specified, it will be retrieved from the callers stack. """

  if module is None:
    frame = sys._getframe(_stackdepth + 1)
    module = frame.f_code.co_name

  return module_type_mappers.get(module, default_type_mapper or DefaultTypeMapper())
