
import decimal
import inspect
import six
import sys

@implements(IDataType)
class ObjectType(object):
  """
  Represents the datatype for an [[Object]] subclass.
  """

  classdef.comparable(['object_cls'])

  def __init__(self, object_cls):
    assert isinstance(object_cls, type), object_cls
    assert issubclass(object_cls, Object), object_cls
    self.object_cls = object_cls

  @override
  def extract(self, locator):
    if not isinstance(locator.value(), abc.Mapping):
      locator.type_error()

    fields = self.object_cls.__fields__
    renames = getattr(self.object_cls.Meta, META.EXTRACT_MAPPING, {})
    strict = getattr(self.object_cls.Meta, META.EXTRACT_STRICT, False)

    kwargs = {}
    handled_keys = set()
    for name, field in fields.items().sortby(lambda x: x[1].priority):
      assert name == field.name, "woops: {}".format((name, field))
      field.extract_kwargs(self.object_cls, locator, kwargs, handled_keys)

    if strict:
      remaining_keys = set(locator.value().keys()) - handled_keys
      if remaining_keys:
        locator.value_error('strict object type "{}" does not allow '
                            'additional keys on extract, but found {!r}'
                            .format(self.object_cls.__name__, remaining_keys))

    obj = object.__new__(self.object_cls)
    obj.__location__ = locator.location_info()
    try:
      obj.__init__(**kwargs)
    except TypeError as exc:
      raise locator.type_error(exc)
    return obj

  @override
  def store(self, locator):
    if not isinstance(locator.value(), self.object_cls):
      locator.type_error()
    result = {}
    for name, field in self.object_cls.__fields__.items():
      value = getattr(locator.value(), name)
      result[field.name] = locator.advance(name, value, field.datatype).store()
    return result

  @override
  def message(self, message_type, data):
    if message_type == MSG_PROPAGATE_FIELDNAME:
      if self.object_cls.__name__ == _InlineObjectTranslator.GENERATED_TYPE_NAME:
        self.object_cls.__name__ = data
    return IDataType['message'](self, message_type, data)



class UnionWrap(object):
  """
  Wraps the value of a Union field.
  """

  classdef.comparable(['datatype', 'value'])
  classdef.def_repr(['datatype', 'value'])

  def __init__(self, datatype, value):
    self.datatype = datatype
    self.value = value


@implements(IDataType)
class UnionType(object):
  """
  A union datatype that expects an object with a "type" key as well as a
  key that has the name of the specified type.
  """

  classdef.comparable(['mapping', 'strict', 'type_key'])

  def __init__(self, mapping, strict=True, type_key='type'):  # type: (Dict[str, IDataType], str, bool) -> None
    self.mapping = {k: translate_field_type(v) for k, v in mapping.items()}
    self.type_key = type_key

  @override
  def child_datatypes(self):
    return self.mapping.values()

  @override
  def extract(self, locator):
    if not isinstance(locator.value(), abc.Mapping):
      locator.type_error()
    if self.type_key not in locator.value():
      locator.type_error()
    type_name = locator.value()[self.type_key]
    if type_name not in locator.value():
      locator.value_error('missing "{}" key'.format(type_name))
    for key in locator.value():
      if key not in (self.type_key, type_name):
        locator.value_error('extra key "{}"'.format(key))
    if type_name not in self.mapping:
      locator.value_error('unexpected "{}": "{}"'.format(self.type_key, type_name))
    datatype = self.mapping[type_name]
    value = locator.advance(type_name, locator.value()[type_name], datatype).extract()
    return UnionWrap(datatype, value)

  @override
  def store(self, locator):
    type_name = locator.value()[self.type_key]
    datatype = self.mapping[type_name]
    return {
      self.type_key: type_name,
      type_name: locator.advance(type_name, locator.value()[type_name], datatype).store()
    }


@implements(IDataType)
class ForwardDecl(object):
  """
  Allows you to forward-declare a type in the current namespace. This is
  necessary for [[Object]]s that reference each other. The type will
  be resolved on-demand.

  Example:

  ```py
  class Wheel(Object):
    car: ForwardDecl('Car')

  class Car(Object):
    wheels: List[Wheel]
  ```
  """

  classdef.comparable(['name', 'frame'])

  def __init__(self, name, frame=None):
    self.name = name
    self.frame = frame or sys._getframe(1)

  def __repr__(self):
    return 'ForwardDecl({!r} in {!r})'.format(self.name, self.frame.f_code.co_filename)

  def resolve(self):
    for mapping in [self.frame.f_locals, self.frame.f_globals]:
      if self.name in mapping:
        x = mapping[self.name]
        break
    else:
      raise RuntimeError('{} could not be resolved'.format(self))
    return translate_field_type(x)

  @override
  def extract(self, locator):
    return self.resolve().extract(locator)

  @override
  def store(self, locator):
    return self.resolve().store(locator)


@implements(IDataType)
class PythonType(object):
  """
  Represents a Python type. No serialize/deserialize capabilities.
  """

  classdef.comparable(['py_type'])

  def __init__(self, py_type):
    assert isinstance(py_type, type)
    self.py_type = py_type

  @override
  def extract(self, locator):
    raise RuntimeError('{!r} cannot be extracted')

  @override
  def store(self, locator):
    raise RuntimeError('{!r} cannot be stored')


from nr.types.structured.locator import Locator
from nr.types.structured.object import Object, META
from nr.types.structured.collection import Collection
from .translator import IFieldTypeTranslator, translate_field_type




@implements(ITypeDefAdapter)
class ForwardDeclTranslator(object):

  def adapt(self, mapper, py_type_def):
    if isinstance(py_type_def, ForwardDecl):
      return py_type_def
    raise InvalidTypeDefinitionError(py_type_def)


@implements(ITypeDefAdapter)
class ObjectAndCollectionTranslator(object):

  def adapt(self, mapper, py_type_def):
    from ..object import Collection, Object
    if isinstance(py_type_def, type) and issubclass(py_type_def, Object):
      return ObjectType(py_type_def)
    elif isinstance(py_type_def, type) and issubclass(py_type_def, Collection):
      return py_type_def.datatype
    raise InvalidTypeDefinitionError(py_type_def)


@implements(ITypeDefAdapter)
class InlineObjectTranslator(object):
  """
  Implements the translation of inline object definitons in dictionary form.
  Example:

  ```py
  datatype = mapper.translate_type_def({
    'a': Field(int),
    'b': Field(str),
  })
  assert type(datatype) == ObjectType
  assert sorted(datatype.object_cls.__fields__.keys()) == ['a', 'b']
  ```
  """

  GENERATED_TYPE_NAME = '_InlineObjectTranslator_generated'

  def adapt(self, mapper, py_type_def):
    from ..object import Object
    if isinstance(py_type_def, dict):
      return ObjectType(type(self.GENERATED_TYPE_NAME, (Object,), py_type_def))
    raise InvalidTypeDefinitionError(py_type_def)


@implements(ITypeDefAdapter)
class ProxyTranslator(object):

  def adapt(self, mapper, py_type_def):
    if isinstance(py_type_def, str):
      return ForwardDecl(py_type_def, cls._find_reference_frame())
    raise InvalidTypeDefinitionError(py_type_def)

  def _find_reference_frame():
    # TODO(@NiklasRosenstein)
    pass


@implements(ITypeDefAdapter)
class PythonTypeTranslator(object):

  priority = -1000

  def adapt(self, mapper, py_type_def):
    if isinstance(py_type_def, type) and py_type_def.__module__ != 'typing':
      return PythonType(py_type_def)
    raise InvalidTypeDefinitionError(py_type_def)

