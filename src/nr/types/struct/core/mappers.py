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
from .interfaces import IConverter, IDataType, IObjectMapper, ITypeMapper, ITypeDefAdapter


@implements(ITypeMapper)
class BaseTypeMapper(object):

  def __init__(self, adapters=None):  # type: (Iterable[ITypeDefAdapter])
    if adapters is None:
      adapters = [x() for x in getattr(self, 'REGISTERED_ADAPTERS', [])]
    self.adapters = list(adapters)

  def __repr__(self):
    return '{!r}(adapters={!r})'.format(type(self).__name__, self.adapters)

  def adapt(self, py_type_def):  # type: (Any) -> IDataType
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

  @classmethod
  def register(cls):
    """ A decorator for classes that implement the [[ITypeDefAdapter]]
    interface to register them with this subclass of the [[BaseTypeMapper]].
    Note that registering converters on the [[BaseTypeMapper]] itself is
    illegal and results in a [[RuntimeError]]. """

    if cls == BaseTypeMapper:
      raise RuntimeError("Cannot register converters on BaseTypeMapper.")

    def decorator(adapter_cls):
      assert ITypeDefAdapter.implemented_by(adapter_cls), \
        "Decorated class does not implemented the ITypeDefAdapter interfaces."

      if 'REGISTERED_ADAPTERS' not in vars(cls):
        cls.REGISTERED_ADAPTERS = []
      cls.REGISTERED_ADAPTERS.append(adapter_cls)
      return adapter_cls

    return decorator


@implements(IObjectMapper)
class BaseObjectMapper(object):
  """ Base class that implements the [[IMapper]] interface. An instance of
  this class can be instantiated directly to build a custom mapper from
  [[ITypeDefAdapter]] and [[IConverter]] implements. Alternatively, it can
  be subclassed and then used with the [[converter()]] decorator. """

  def __init__(self, converters=None):  # type: (Iterable[IConverter])
    if converters is None:
      converters = [x() for x in getattr(self, 'REGISTERED_CONVERTERS', [])]
    self.converters = list(converters)

  def __repr__(self):
    return '{!r}(converters={!r})'.format(type(self).__name__, self.converters)

  def get_converter_for_datatype(self, datatype):  # type: (IDataType) -> IConverter
    """ Returns the first [[IConverter]] matching the specified datatype. """

    for converter in self.converters:
      if converter.accept(datatype):
        return converter
    raise RuntimeError('unsupported datatype {}'.format(datatype))  # TODO: Proper error type

  def deserialize(self, location):
    converter = self.get_converter_for_datatype(location.datatype)
    return converter.deserialize(self, location)

  def serialize(self, location):
    converter = self.get_converter_for_datatype(location.datatype)
    return converter.serialize(self, location)

  @classmethod
  def register(cls):
    """ A decorator for classes that implement the [[IConverter]] interface
    to register them with this subclass of the [[BaseObjectMapper]]. Note
    that registering converters on the [[BaseObjectMapper]] itself is illegal
    and results in a [[RuntimeError]]. """

    if cls == BaseObjectMapper:
      raise RuntimeError("Cannot register converters on BaseObjectMapper.")

    def decorator(converter_cls):
      assert IConverter.implemented_by(converter_cls), \
        "Decorated class does not implemented the IConverter interfaces."

      if 'REGISTERED_CONVERTERS' not in vars(cls):
        cls.REGISTERED_CONVERTERS = []
      cls.REGISTERED_CONVERTERS.append(converter_cls)
      return converter_cls

    return decorator


__all__ = ['BaseTypeMapper', 'BaseObjectMapper']
