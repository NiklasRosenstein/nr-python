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

__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
__version__ = '0.0.1'

from nr.pylang.utils import NotSet
import inspect
import nr.pylang.utils.classdef
import nr.interface
import string

### Error classes
#################

class SerializationError(Exception):

  def __init__(self, node, message=None):  # type: (Node, Optional[str])
    if not isinstance(node, Node):
      raise TypeError('node must be a Location object, got {}'.format(
        type(node).__name__))
    self.node = node
    self.message = message

  def __str__(self):
    result = 'at {}'.format(self.node.locator)
    if self.node.context.filename:
      result = 'in "{}": '.format(self.node.context.filename) + result
    if self.message:
      result += ': ' + str(self.message)
    return result


class SerializationTypeError(SerializationError):

  def __init__(self, node, message=None):  # type: (Location, Optional[str])
    if message is None:
      expected = node.datatype.to_human_readable()
      got = type(node.value).__name__
      message = 'expected "{}", got "{}"'.format(expected, got)
    super(SerializationTypeError, self).__init__(node, message)


class SerializationValueError(SerializationError):
  pass


class InvalidTypeDefinitionError(Exception):

  def __init__(self, py_type_def):
    self.py_type_def = py_type_def

  def __str__(self):
    return repr(self.py_type_def)


### Interfaces
##############

class IDataType(nr.interface.Interface):
  """
  Interface for datatypes. A datatype usually has a one to one mapping
  with a Python type. The serialization/deserialization of the type to other
  realms is handled by the #IDeserializer and #ISerializer interfaces.

  Datatypes must be comparable. The default string representation is derived
  from the constructor arguments. Datatypes may also provide a more easily
  readable representation with #to_human_readable().

  A datatype also describes how it can be created from a more Pythonic
  description via the #from_typedef() function.

  To implement an #IDataType, it is recommendable to use #nr.pylang.utils.\\
  classdef.comparable() in order to implement `__hash__()`, `__eq__()` and
  `__ne__()` in.
  """

  nr.pylang.utils.classdef.comparable([])  # adds __hash__, __eq__, __ne__ to the interface

  @nr.interface.default
  @classmethod
  def priority(cls):
    return 0

  @nr.interface.default
  def to_human_readable(self):  # type: () -> str
    return type(self).__name__

  @nr.interface.default
  def propagate_field_name(self, name):  # type: (str) -> None
    """ This method is called when the datatype instance is attached to a
    field in an object. The name of the field is passed to this method. This
    is used for the inline object definition. """

  @classmethod
  def from_typedef(cls, recursive, py_type_def):  # type: (Callable, Any) -> IDataType
    # raises: InvalidTypeDefinitionError
    """ Convert the datatype from a pure Python description. Raise an
    #InvalidTypeDefinitionError if the *py_type_def* cannot be translated to
    this datatype. """

  def isinstance_check(self, py_value, strict, coerce):  # type: (Any, bool, bool) -> Any
    """ This method returns *py_value*, or an adaptation of *py_value*, if it
    matches the datatype. If it doesn't, a [[TypeError]] with the reason is
    raised.

    raises TypeError: If the *py_value* doesn't match this datatype. """


class IDeserializer(nr.interface.Interface):
  " Interface for deserializing values of a given #IDataType. "

  def deserialize(self, mapper, node):  # type: (ObjectMapper, Node) -> Any
    pass


class ISerializer(nr.interface.Interface):
  " Interface for serializing values of a given #IDataType. "

  def serialize(self, mapper, node):  # type: (ObjectMapper, Node) -> Any
    pass


### Supporting classes for (de-) serialization.
###############################################

class Locator(object):
  """
  A locator is basically a wrapper for a list of strings or integer indices
  that represents the location of an element in an object tree.

  Locator objects are immutable.
  """

  _WHITELISTED_KEY_CHARACTERS = string.ascii_letters + string.digits + '_-'

  def __init__(self, items):
    self._items = items

  __iter__ = lambda self: iter(self._items)
  __len__ = lambda self: len(self._items)
  __getitem__ = lambda self, index: self._items[index]
  __repr__ = lambda self: 'Locator({})'.format(str(self))
  __bool__ = lambda self: bool(self._items)
  __nonzero__ = __bool__

  def __str__(self):
    parts = ['$']
    for item in self._items:
      if isinstance(item, int):
        parts.append('[' + str(item) + ']')
      else:
        item = str(item)
        if '"' in item:
          item = item.replace('"', '\\"')
        if any(c not in self._WHITELISTED_KEY_CHARACTERS for c in item):
          item = '"' + item + '"'
        parts.append('.' + item)
    return ''.join(parts)

  def access(self, root):  # type: (Union[List, Dict]) -> Any
    """
    Accesses the value represented by this Locator object starting from *root*.

    >>> root = {'values': [1, 2, 3]}
    >>> from nr.databind.core.context import Locator
    >>> Locator(['values', 1]).access(root)
    2

    :param root: The object to start indexing from.
    :raises KeyError: If an item in an object cannot be accessed.
    :raises IndexError: If an item in a list cannot be accessed.
    ``` """

    value = root
    for item in self._items:
      try:
        value = value[item]
      except KeyError as exc:
        raise KeyError(str(self))
      except IndexError as exc:
        raise IndexError('{} at {}'.format(exc, self))

    return value

  def append(self, item):  # type: (Union[str, int]) -> Locator
    " Creates a copy of this locator and appends *item* to it. "

    items = list(self._items)
    items.append(item)
    return Locator(items)

  def pop(self, item):  # type: () -> Locator
    " Creates a copy of this locator and removes the last item from it. "

    items = list(self._items)
    items.pop()
    return Locator(items)


class Context(object):
  """
  A Context object contains all information that is mostly constant during the
  same (de-) serialization process.

  :param parent: The parent Context object. This is usually None unless a (de-)
    serializer decides to create a new sub-context.
  :param filename: The name of the file from which the data for the (de-)
    serialization originates. This is useful in case of an exception which can
    then include this filename for informational purposes.
  :param decorations: A list of decorations that apply to the context.
  """

  def __init__(self, parent, filename, decorations=None):
    # type: (Optional[Context], Optional[str], Optional[List[Decoration]]) -> None
    if parent is not None and not isinstance(parent, Context):
      raise TypeError('parent must be None or Context, got "{}"'.format(type(parent).__name__))
    if filename is not None and not isinstance(filename, str):
      raise TypeError('filename must be None or str, got "{}"'.format(type(filename).__name__))
    self.parent = parent
    self.filename = filename
    self.decorations = decorations or []


class Node(object):
  """
  A Node represents a value in a tree during (de-) serialization.

  :param parent: The parent node which represents the parent value.
  :param context: The Context object that is used for this node's processing.
  :param locator: A Locator object that describes the location of the node in
    the tree.
  :param datatype: The expected datatype of the node.
  :param value: The value of the node that is to be (de-) serialized.
  :param decorations: A list of decorations that apply to the node.
  """

  def __init__(self, parent, context, locator, datatype, value, decorations=None, prev_sibling=None):
    datatype = translate_type_def(datatype) if datatype is not None else None
    # type: (Optional[Node], Context, Locator, IDataType, Any, Optional[List[Decoration]]) -> None
    if parent is not None and not isinstance(parent, Node):
      raise TypeError('parent must be None or Node, got "{}"'.format(type(parent).__name__))
    if prev_sibling is not None and not isinstance(prev_sibling, Node):
      raise TypeError('prev_sibling must be None or Node, got "{}"'.format(type(prev_sibling).__name__))
    if not isinstance(context, Context):
      raise TypeError('context must be Context, got "{}"'.format(type(context).__name__))
    if not isinstance(locator, Locator):
      raise TypeError('locator must be Locator, got "{}"'.format(type(locator).__name__))
    if datatype is not None and not IDataType.provided_by(datatype):
      raise TypeError('datatype must be IDataType, got "{}"'.format(type(datatype).__name__))
    self.parent = parent
    self.prev_sibling = prev_sibling
    self.context = context
    self.locator = locator
    self.datatype = ProxyType.deref(datatype)
    self.value = value
    self.decorations = decorations or []
    self.result = None
    self.unknowns = set()
    collect = get_decoration(Collect, context.decorations)
    if collect:
      collect.nodes.append(self)

  def __repr__(self):
    return 'Node(locator={!r}, datatype={!r})'.format(self.locator, self.datatype)

  def type_error(self, message=None):  # type: (Optional[str]) -> SerializationTypeError
    " A helper function to create a #SerializationTypeError object. "

    return SerializationTypeError(self, message)

  def value_error(self, message=None):  # type: (Optional[str]) -> SerializationValueError
    " A helper function to create a #SerializationValueError object. "

    return SerializationValueError(self, message)

  def get_decoration(self, decoration_cls):  # type: (Type[Decoration]) -> Optional[Decoration]
    """
    Return the first decoration found for the *decoration_cls* in the Context's
    decorations, the Node's decorations, or, if applicable, the classes'
    decorations.
    """

    decoration = get_decoration(decoration_cls, self.context.decorations, self.decorations)
    if not decoration and isinstance(decoration_cls, ClassDecoration):
      if isinstance(self.datatype, StructType):
        decoration = decoration_cls.get(self.datatype.struct_cls)
      elif isinstance(self.datatype, PythonClassType):
        decoration = decoration_cls.get(self.datatype.cls)

    return decoration

  def get_local_decoration(self, decoration_cls):  # type: (Type[Decoration]) -> Optional[Decoration]
    """
    Return the first decoration found for the *decoration_cls* in the Node's
    decorations.
    """

    return get_decoration(decoration_cls, self.decorations)

  def make_child(self, key, datatype, value, context=None, decorations=None):
    return Node(self, context or self.context, self.locator.append(key),
                datatype, value, decorations)

  def replace(self, locator=NotSet, datatype=NotSet, value=NotSet, context=NotSet):
    locator = self.locator if locator is NotSet else locator
    datatype = self.datatype if datatype is NotSet else datatype
    value = self.value if value is NotSet else value
    context = self.context if context is NotSet else context
    return Node(None, context, locator, datatype, value, self.decorations, prev_sibling=self)

  @property
  def key(self):  # type: () -> Union[None, int, str]
    if self.locator:
      return self.locator[-1]
    else:
      return None


class Decoration(object):
  """
  Base class for decorations. Decorations can be attached to objects in order
  to customize the (de-) serialization process or the behavior of related types.

  * A #Context can have a list of decorations that influence the (de-) serialization
    behavior globally.
  * A #Node can have a list of decorations that influence the behavior (de-)
    serialization behavior locally.
  * #Field#s for #Struct#s can have decorations attached that influence the behavior
    for just the (de-) serialization for that field.
  * Classes can have decorations (in their `__decorations__` member) that may be
    respected during (de-) serialization.
  """


class SerializerCollection(object):
  """
  A collection of (de-) serializers. Serializers can be registered by association
  with the #IDataType that they are a (de-) serializer for or with a test callable.
  """

  def __init__(self, interface):
    self._interface = interface
    self._mapping = {}  # type: Dict[IDataType, interface]
    self._pytype_mapping = {}  # type: Dict[Type, interface]
    self._tests = []  # type: List[Tuple[Callable[[IDataType], Bool], interface]

  def register(self, arg, impl):
    """
    Registers a new #IDataType or test function along with  a(de-) serializer.
    """

    # Is this type applicable for the PythonClassType?
    is_pytype = False
    if isinstance(arg, type):
      try:
        PythonClassType.from_typedef(None, arg)
        is_pytype = True
      except InvalidTypeDefinitionError as exc:
        # It is not. :-)
        pass

    if not is_pytype and self._interface and not self._interface.provided_by(impl):
      raise TypeError('expected {} implementation, got {}'.format(
        self._interface.__name__, type(impl).__name__))

    if is_pytype:
      self._pytype_mapping[arg] = impl
    elif isinstance(arg, type) and (not self._interface or IDataType.implemented_by(arg)):
      self._mapping[arg] = impl
    elif inspect.isfunction(arg):
      self._tests.append((arg, impl))
    else:
      raise TypeError('expected IDataType or function, got {}'.format(type(arg).__name__))

  def match(self, datatype):
    for test_func, impl in self._tests:
      if test_func(datatype):
        return impl
    if isinstance(datatype, PythonClassType):
      try:
        return self._pytype_mapping[datatype.cls]
      except KeyError:
        pass
    try:
      return self._mapping[type(datatype)]
    except KeyError:
      pass
    return None


class Module(object):
  """
  A module is a collection of (de-) serializers. Modules can also be combined
  into one single module. Modules implement the #IDeserializeDispatcher and
  #ISerializeDispatcher interface.
  """

  def __init__(self, *submodules):
    self._serializers = SerializerCollection(ISerializer)
    self._deserializers = SerializerCollection(IDeserializer)
    self._submodules = []
    for module in submodules:
      self.register(module)

  def register(self, value, impl=None):
    if impl is None:
      if not isinstance(value, Module):
        raise TypeError('argument 1 must be a Module if argument 2 is omitted, got "{}"'
                        .format(type(value).__name__))
      self._submodules.append(value)
    else:
      valid = False
      if ISerializer.provided_by(impl):
        self._serializers.register(value, impl)
        valid = True
      if IDeserializer.provided_by(impl):
        self._deserializers.register(value, impl)
        valid = True
      if not valid:
        raise TypeError('argument 2 must implement ISerializer/IDeserializer, got "{}"'
                        .format(type(impl).__name__))

  def get_serializer(self, datatype):
    result = self._serializers.match(datatype)
    if result is None:
      for module in self._submodules:
        result = module.get_serializer(datatype)
        if result is not None:
          break
    return result

  def get_deserializer(self, datatype):
    result = self._deserializers.match(datatype)
    if result is None:
      for module in self._submodules:
        result = module.get_deserializer(datatype)
        if result is not None:
          break
    return result


class ObjectMapper(Module):
  """
  The ObjectMapper is an extension of the #Module class that provides additional
  functions to dispatch the (de-) serialization from an initial state.
  """

  def deserialize_node(self, node):  # type: (Node) -> Any
    deserializer = self.get_deserializer(node.datatype)
    if not deserializer:
      raise node.type_error('no deserializer was found for datatype {!r}'.format(node.datatype))
    node.result = deserializer.deserialize(self, node)
    return node.result

  def serialize_node(self, node):  # type: (Node) -> Any
    serializer = self.get_serializer(node.datatype)
    if not serializer:
      raise node.type_error('no serializer was found for datatype {!r}'.format(node.datatype))
    node.result = serializer.serialize(self, node)
    return node.result

  def deserialize_to_node(self, *args, **kwargs):  # type: (...) -> Node
    node = make_node(*args, **kwargs)
    self.deserialize_node(node)
    return node

  def serialize_to_node(self, *args, **kwargs):  # type: (...) -> Node
    node = make_node(*args, **kwargs)
    self.serialize_node(node)
    return node

  def deserialize(self, *args, **kwargs):  # type: (...) -> Any
    return self.deserialize_node(make_node(*args, **kwargs))

  def serialize(self, *args, **kwargs):  # type: (...) -> Any
    return self.serialize_node(make_node(*args, **kwargs))


def make_node(value, datatype, filename=None, decorations=None):
  # type: (Any, Any, Optional[str], Optional[List[Decoration]]) -> (Context, Node)
  datatype = translate_type_def(datatype)
  context = Context(None, filename, decorations)
  node = Node(None, context, Locator([]), datatype, value)
  return node


### Feature imports
###################

from .collection import Collection
from .datatypes import *
from .decorations import *
from .struct import Field, Struct, StructType
from .union import UnionType
