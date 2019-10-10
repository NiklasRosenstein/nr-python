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

from nr.types.interface import implements
from .errors import InvalidTypeDefinitionError
from .interfaces import IConverter, IDataType, IMapper, ITypeDefAdapter


@implements(IMapper)
class Mapper(object):
  """
  The default mapper implementation. Constructing it without arguments
  initializes the mapper with all known [[ITypeDefAdapter]] implementations
  from the [[adapters]] module as well as all known implementations of the
  [[IConverter]] interface in the `'json'` namespace.
  """

  def __init__(self, adapters=None, converters=None, namespace='json'):
    if adapters is None:
      adapters = [x() for x in ITypeDefAdapter.implementations() if
                  x.__module__ == 'nr.types.structured.core.adapters']
      adapters.sort(key=lambda x: x.priority)
    self.adapters = adapters

    if converters is None:
      converters = [x() for x in IConverter.implementations() if
                    x.namespace == namespace]
      converters.sort(key=lambda x: x.priority)
    self.converters = converters

  def __repr__(self):
    return 'Mapper(adapters={!r}, converters={!r})'.format(
      self.adapters, self.converters)

  def translate_type_def(self, py_type_def):  # type: (Any) -> IDataType
    """
    Translates a Python type declaration to an [[IDataType]] object. If the
    translation fails, a [[InvalidTypeDefinitionError]] is raised.
    """

    if IDataType.provided_by(py_type_def):
      return py_type_def
    elif isinstance(py_type_def, type) and IDataType.implemented_by(py_type_def):
      return py_type_def()
    for adapter in self.adapters:
      try:
        return adapter.adapt(self, py_type_def)
      except InvalidTypeDefinitionError:
        pass
    raise InvalidTypeDefinitionError(py_type_def)

  def get_converter_for_datatype(self, datatype):  # type: (IDataType) -> IConverter
    """
    Returns the first [[IConverter]] matching the specified datatype.
    """

    for converter in self.converters:
      if converter.accept(datatype):
        return converter
    raise RuntimeError('unsupported datatype {}'.format(datatype))  # TODO

  def deserialize(self, location):
    converter = self.get_converter_for_datatype(location.datatype)
    return converter.deserialize(self, location)

  def serialize(self, location):
    converter = self.get_converter_for_datatype(location.datatype)
    return converter.serialize(self, location)


__all__ = ['Mapper']
