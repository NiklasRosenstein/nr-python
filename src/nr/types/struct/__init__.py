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

import contextlib
import logging
import sys
import traceback

from nr.types.utils.module import get_calling_module_name
from .core import *

_default_type_mapper = None
_context_type_mappers = []  # TODO (@NiklasRosenstein): Thread-local
_module_type_mappers = {}


@contextlib.contextmanager
def override_type_mapper(mapper):  # type: (ITypeMapper) -> ContextManager
  _context_type_mappers.append(mapper)
  try: yield
  finally:
    assert _context_type_mappers.pop() == mapper


def set_type_mapper(module, mapper):  # type: (str, ITypeMapper)
  """ Sets the type mapper for a module. """

  logger = logging.getLogger(__name__)
  logger.debug("Setting ITypeMapper for module {!r} to {!r}.".format(
    module, mapper))
  _module_type_mappers[module] = mapper


def set_default_type_mapper(mapper):  # type: ()
  """ Sets the default type mapper. """

  logger = logging.getLogger(__name__)
  logger.debug("Setting default ITypeMapper to {!r}.".format(mapper))
  global _default_type_mapper
  _default_type_mapper = mapper


def get_type_mapper(module=None, _stackdepth=0):  # type: (Optional[str], int) -> ITypeMapper
  """ Retrieves the type mapper for the specified *module*. If no module is
  specified, it will be retrieved from the callers stack. """

  if _context_type_mappers:
    mapper = _context_type_mappers[-1]
  else:
    module = module or get_calling_module_name(_stackdepth+1)
    mapper = _module_type_mappers.get(module,
      _default_type_mapper or DefaultTypeMapper())

  stacktrace = '\n'.join(traceback.format_stack(limit=_stackdepth + 3))
  logger = logging.getLogger(__name__)
  logger.debug('get_type_mapper(module={!r}, _stackdepth={!r}) -> {!r}\n\n{}'
               .format(module, _stackdepth, mapper, stacktrace))

  return mapper


from .struct import *

__all__ = (
  core.__all__ +
  struct.__all__
)
