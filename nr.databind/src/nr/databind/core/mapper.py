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

from .datatypes import PythonClassType, translate_type_def
from .decoration import DeserializeAs, get_decoration
from .errors import (
  InvalidTypeDefinitionError,
  SerializationTypeError,
  SerializationValueError)
from .interfaces import (
  IDataType,
  IDeserializeContext,
  ISerializeContext,
  IDeserializer,
  ISerializer)
from .location import Location, Path
from nr.interface import Interface, default, implements, override
import contextlib
import functools
import inspect

__all__ = ['IModule', 'SimpleModule', 'ObjectMapper']


class IModule(Interface):

  def get_deserializer(self, datatype):
    pass

  def get_serializer(self, datatype):
    pass


@implements(IModule)
class SimpleModule(object):
  """ A collection of serializers and deserializers. """

  def __init__(self):
    self._deserializers = {}
    self._serializers = {}
    self._checked_deserializers = []
    self._checked_serializers = []

  def _wrap_serializer_function(self, func):
    @functools.wraps(func)
    def wrapper(context, location):
      try:
        return func(context, location)
      except ValueError as exc:
        raise SerializationValueError(location, exc)
      except TypeError as exc:
        raise SerializationTypeError(location, exc)
    return wrapper

  def deserializer_for(self, datatype_type):
    """ A decorator to register a deserializer function for the specified
    *datatype_type*. The decorator simply calls #register_deserializer()
    with the specified datatype and decorated function after wrapping the
    function in a #IDeserializer. """

    def decorator(func):
      self.register_deserializer(datatype_type, IDeserializer(self._wrap_serializer_function(func)))
      return func

    return decorator

  def serializer_for(self, datatype_type):
    """ Analoguous to #deserializer_for(). """

    def decorator(func):
      self.register_serializer(datatype_type, func)
      return func

    return decorator

  def _coerce_datatype_type(self, datatype_type):
    if isinstance(datatype_type, type) and IDataType.implemented_by(datatype_type):
      return datatype_type
    try:
      type_def = translate_type_def(datatype_type)
      if isinstance(type_def, PythonClassType):
        return PythonClassType.make_check(datatype_type)
    except InvalidTypeDefinitionError:
      pass
    return datatype_type

  def register_deserializer(self, datatype_type, deserializer):
    """ Registers a deserializer with an associated datatype or a predicate
    function. The *datatype_type* may be one of the following types:

    1. An instance of the #IDeserializer interface
    2. A function object that accepts an #IDataType instance and returns
        True if the *deserializer* is applicable to the datatype
    """

    if inspect.isfunction(deserializer):
      deserializer = IDeserializer(self._wrap_serializer_function(deserializer))

    datatype_type = self._coerce_datatype_type(datatype_type)

    if not IDeserializer.provided_by(deserializer):
      raise TypeError('expected IDeserializer instance, got {!r}'
        .format(deserializer.__name__))
    if inspect.isfunction(datatype_type):
      self._checked_deserializers.append((datatype_type, deserializer))
      return
    if not IDataType.implemented_by(datatype_type):
      raise ValueError('expected IDataType implementation, got {!r}'
        .format(datatype_type.__name__))
    self._deserializers[datatype_type] = deserializer

  def register_serializer(self, datatype_type, serializer):
    """ Analoguous to #register_deserializer(). """

    if inspect.isfunction(serializer):
      serializer = ISerializer(self._wrap_serializer_function(serializer))

    datatype_type = self._coerce_datatype_type(datatype_type)

    if not ISerializer.provided_by(serializer):
      raise TypeError('expected IDeserializer instance, got {!r}'
        .format(serializer.__name__))
    if inspect.isfunction(datatype_type):
      self._checked_serializers.append((datatype_type, serializer))
      return
    if not IDataType.implemented_by(datatype_type):
      raise ValueError('expected IDataType implementation, got {!r}'
        .format(datatype_type.__name__))
    self._serializers[datatype_type] = serializer

  def register_duplex(self, datatype_type, deserializer_serializer):
    """ Analoguous to #register_deserializer(), only that the registered
    instance must implement both the #IDeserializer and #ISerializer
    interfaces. """

    self.register_deserializer(datatype_type, deserializer_serializer)
    self.register_serializer(datatype_type, deserializer_serializer)

  @override
  def get_deserializer(self, datatype):
    for check, deserializer in self._checked_deserializers:
      if check(datatype):
        return deserializer
    try:
      return self._deserializers[type(datatype)]
    except KeyError:
      return None

  @override
  def get_serializer(self, datatype):
    for check, serializer in self._checked_serializers:
      if check(datatype):
        return serializer
    try:
      return self._serializers[type(datatype)]
    except KeyError:
      return None


@implements(IModule)
class ModuleContainer(object):
  """ Container for #IModule's. """

  def __init__(self, *modules):
    self._modules = []
    for module in modules:
      if isinstance(module, type):
        module = module()
      self.register_module(module)

  def register_module(self, module):
    if not IModule.provided_by(module):
      raise TypeError('expected IModule implementation, got {!r}'
        .format(type(module).__name__))
    self._modules.append(module)

  @override
  def get_deserializer(self, datatype):
    for module in self._modules:
      deserializer = module.get_deserializer(datatype)
      if deserializer is not None:
        return deserializer
    return None

  @override
  def get_serializer(self, datatype):
    for module in self._modules:
      serializer = module.get_serializer(datatype)
      if serializer is not None:
        return serializer
    return None


@implements(IDeserializeContext, ISerializeContext)
class ModuleContext(object):

  def __init__(self, module, path, filename, decorations):
    # type: (IModule, Optional[list], Optional[str])
    self._module = module
    self._filename = [filename] if filename else []
    self._path = list(path) if path else []
    self._decorations = list(decorations)

  @property
  def path(self):
    return Path(self._path[:])

  @property
  def filename(self):
    if self._filename:
      return self._filename[-1]
    return None

  @contextlib.contextmanager
  def _enter(self, key, filename):
    if key is not None and not isinstance(key, (list, tuple)):
      key = [key]
    if key is not None:
      self._path.extend(key)
    if filename is not None:
      self._filename.append(filename)
    try:
      yield
    finally:
      if key is not None:
        for item in reversed(key):
          assert self._path.pop() is item, item
      if filename is not None:
        assert self._filename.pop() is filename, filename

  def mklocation(self, value, datatype, decorations):
    return Location(value, datatype, self.path, self.filename, decorations)

  @override
  def deserialize(self, value, datatype, key=None, filename=None, decorations=None):
    datatype = translate_type_def(datatype)
    # Handle the DeserializeAs decoration.
    if isinstance(datatype, PythonClassType):
      deserialize_as = get_decoration(DeserializeAs, datatype.cls)
      if deserialize_as:
        datatype = deserialize_as.datatype
    with self._enter(key, filename):
      deserializer = self._module.get_deserializer(datatype)
      if deserializer is None:
        raise RuntimeError('no deserializer for {!r} found'.format(
          type(datatype).__name__))
      return deserializer.deserialize(self, self.mklocation(value, datatype, decorations))

  @override
  def serialize(self, value, datatype, key=None, filename=None, decorations=None):
    datatype = translate_type_def(datatype)
    with self._enter(key, filename):
      serializer = self._module.get_serializer(datatype)
      if serializer is None:
        raise RuntimeError('no serializer for {!r} found'.format(
          type(datatype).__name__))
      return serializer.serialize(self, self.mklocation(value, datatype, decorations))

  @override
  def iter_decorations(self):
    return iter(self._decorations)


class ObjectMapper(SimpleModule):
  """ The #ObjectMapper is a high-level entrypoint for the deserialization/
  serialization process, dispatching the workload to a #ModuleContext. The
  object mapper can be initialized from an argument list of #IModule objects.
  """

  def __init__(self, *modules):
    super(ObjectMapper, self).__init__()
    self._modules = [x() if isinstance(x, type) else x for x in modules]
    self._decorations = []

  def module_container(self):  # type: () -> ModuleContainer
    return ModuleContainer(self, *self._modules)

  def add_decorations(self, *decorations):  # type: (Decoration) -> ObjectMapper
    """ Permanently adds the specified *decorations* to the mapper. """

    self._decorations.extend(decorations)
    return self

  def register_module(self, module):  # type: (IModule) -> ObjectMapper
    """ Registers an #IModule instance in the mapper. """

    self._modules.append(module)
    return self

  def deserialize(self, value, datatype, path=None, filename=None, decorations=None):
    # type: (Any, Any, Optional[Path], Optional[str], Optional[List[Decoration]]) -> Any
    """ Deserializes *value* from *datatype* with the modules that are
    registered in the ObjectMapper. Returns the deserialized result. """

    decorations = list(self._decorations) + list(decorations or ())
    context = ModuleContext(self.module_container(), path, filename, decorations)
    return context.deserialize(value, datatype)

  def serialize(self, value, datatype, path=None, filename=None, decorations=None):
    # type: (Any, Any, Optional[Path], Optional[str], Optional[List[Decoration]]) -> Any
    """ Serializes *value* as *datatype* with the modules that are registered
    in the ObjectMapper. Returns the deserialized result. """

    decorations = list(self._decorations) + list(decorations or ())
    context = ModuleContext(self.module_container(), path, filename, decorations)
    return context.serialize(value, datatype)
