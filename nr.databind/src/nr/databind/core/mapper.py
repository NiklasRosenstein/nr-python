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

from .datatypes import translate_type_def
from .interfaces import IDataType, IDeserializeContext, \
  ISerializeContext, IDeserializer, ISerializer
from .location import Location, Path
from nr.interface import Interface, default, implements, override
import contextlib

__all__ = ['IModule', 'SimpleModule', 'ObjectMapper']


class IModule(Interface):

  def setup_module(self, context):
    """ Called to initialize the module. This is currently unused and only
    part of the interface for future extension. The *context* argument will
    be None. """

    pass

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

  def register_deserializer(self, datatype_type, deserializer):
    if not IDataType.implemented_by(datatype_type):
      raise ValueError('expected IDataType implementation, got {!r}'
        .format(datatype_type.__name__))
    if not IDeserializer.provided_by(deserializer):
      raise TypeError('expected IDeserializer instance, got {!r}'
        .format(deserializer.__name__))
    self._deserializers[datatype_type] = deserializer

  def register_serializer(self, datatype_type, serializer):
    if not IDataType.implemented_by(datatype_type):
      raise ValueError('expected IDataType implementation, got {!r}'
        .format(datatype_type.__name__))
    if not ISerializer.provided_by(serializer):
      raise TypeError('expected IDeserializer instance, got {!r}'
        .format(serializer.__name__))
    self._serializers[datatype_type] = serializer

  def register_duplex(self, datatype_type, deserializer_serializer):
    self.register_deserializer(datatype_type, deserializer_serializer)
    self.register_serializer(datatype_type, deserializer_serializer)

  def setup_module(self, context):
    pass

  def get_deserializer(self, datatype):
    try:
      return self._deserializers[type(datatype)]
    except KeyError:
      return None

  def get_serializer(self, datatype):
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

  def setup_module(self, context):
    for module in self._modules:
      module.setup_module(context)

  def get_deserializer(self, datatype):
    for module in self._modules:
      deserializer = module.get_deserializer(datatype)
      if deserializer is not None:
        return deserializer
    return None

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
  def _put_key(self, key, filename):
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

  def mklocation(self, value, datatype):
    return Location(value, datatype, self.path, self.filename)

  @override
  def deserialize(self, value, datatype, key=None, filename=None):
    datatype = translate_type_def(datatype)
    with self._put_key(key, filename):
      deserializer = self._module.get_deserializer(datatype)
      if deserializer is None:
        raise RuntimeError('no deserializer for {!r} found'.format(
          type(datatype).__name__))
      return deserializer.deserialize(self, self.mklocation(value, datatype))

  @override
  def serialize(self, value, datatype, key=None, filename=None):
    datatype = translate_type_def(datatype)
    with self._put_key(key, filename):
      serializer = self._module.get_serializer(datatype)
      if serializer is None:
        raise RuntimeError('no serializer for {!r} found'.format(
          type(datatype).__name__))
      return serializer.serialize(self, self.mklocation(value, datatype))

  @override
  def decorations(self):
    return iter(self._decorations)


class ObjectMapper(object):
  """ The #ObjectMapper is a high-level entrypoint for the deserialization/
  serialization process, dispatching the workload to a #ModuleContext. The
  object mapper can be initialized from an argument list of #IModule objects.
  """

  def __init__(self, *modules):
    self._modules = ModuleContainer(*modules)
    self._modules.setup_module(None)
    self._decorations = []

  def add_decorations(self, *decorations):
    self._decorations.extend(decorations)

  def register_module(self, module):
    self._modules.register_module(module)
    module.setup_module()

  def deserialize(self, value, datatype, path=None, filename=None, decorations=None):
    decorations = list(self._decorations) + list(decorations or ())
    context = ModuleContext(self._modules, path, filename, decorations)
    return context.deserialize(value, datatype)

  def serialize(self, value, datatype, path=None, filename=None, decorations=None):
    decorations = list(self._decorations) + list(decorations or ())
    context = ModuleContext(self._modules, path, filename, decorations)
    return context.serialize(value, datatype)
