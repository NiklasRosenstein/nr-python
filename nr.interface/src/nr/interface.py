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
__version__ = '0.0.4'

__all__ = [
  'FunctionSpec',
  'Interface',
  'Implementation',
  'ImplementationError',
  'ConflictingInterfacesError',
  'is_interface',
  'implements',
  'attr',
  'staticattr',
  'default',
  'final',
  'override',
  'optional',
]

import inspect
import itertools
import six
import sys
import types

from nr.collections import OrderedSet
from nr.metaclass.copy import copy_class
from nr.metaclass.inline import InlineMetaclassBase
from nr.pylang.utils import NotSet
from nr.pylang.utils.classdef import make_singleton
#from typing import Any, Dict, List, Optional

_NoCheckType = make_singleton('_NoCheckType')


class FunctionSpec(object):
  """ Represents a function argument specification. This is a re-implementation
  of the #inspect.FulLArgSpec class (as it is not available in all Python 2).
  """

  def __init__(self,
      args=None,            # type: Optional[List[str]]
      varargs=None,         # type: Optional[str]
      varkw=None,           # type: Optional[str]
      defaults=None,        # type: Optional[List[Any]]
      kwonlyargs=None,      # type: Optional[List[str]]
      kwonlydefaults=None,  # type: Optional[Dict[str, Any]]
      annotations=None      # type: Optional[Dict[str, Any]]
      ):
    self.args = args or []
    self.varargs = varargs
    self.varkw = varkw
    self.defaults = defaults or []
    self.kwonlyargs = kwonlyargs or []
    self.kwonlydefaults = kwonlydefaults or {}
    self.annotations = annotations or {}

  def __eq__(self, other):
    if type(other) != type(self):
      return False
    for key in ('args', 'varargs', 'varkw', 'defaults', 'kwonlyargs',
                'kwonlydefaults', 'annotations'):
      if getattr(self, key) != getattr(other, key):
        return False
    return True

  def __ne__(self, other):
    return not (self == other)

  @classmethod
  def from_function(cls, func):
    """ Reads the signature of a function using #inspect.getfullargspec()
    (or #inspect.getargspec() depending on which is available). If *func*
    is a #classmethod or #staticmethod, it is first unwrapped. """

    if isinstance(func, (classmethod, staticmethod)):
      if hasattr(func, 'im_func'):
        func = func.im_func
      elif hasattr(func, '__func__'):
        func = func.__func__
      elif isinstance(func, staticmethod):
        # Python 2.6 workaround
        func = type('t', (object,), {'func': func}).func
      elif isinstance(func, classmethod):
        # Python 2.6 workaround
        func = type('t', (object,), {'func': func}).func.im_func
      else:
        raise RuntimeError('unable to get wrapped function from {0} object'.format(
          type(func).__name__))

    if hasattr(inspect, 'getfullargspec'):
      argspec = inspect.getfullargspec(func)
      return cls(argspec.args, argspec.varargs, argspec.varkw,
        list(argspec.defaults or []), argspec.kwonlyargs, argspec.kwonlydefaults,
        argspec.annotations)
    else:
      argspec = inspect.getargspec(func)
      return cls(argspec.args, argspec.varargs, argspec.keywords,
        list(argspec.defaults or []))

  def conformity_check(self, other):  # type: (FunctionSpec) -> Optional[str]
    """ Checks if *self* conforms with the *other* function spec. The spec
    is conformant with another spec if it satisfies the minimum requirements
    imposed by *other*.

    Returns a messages that describe why *self* is not a conformant of
    *other*. If None is returned, *self* is conformant. """

    # Check if overlapping positional arguments are the same.
    overlapping_args = self.args[:len(other.args)]
    if overlapping_args != other.args:
      return 'overlapping positional argument names do not match '\
        '({0!r} != {1!r})'.format(overlapping_args, other.args)

    # Check that additional positional arguments have default values.
    if len(self.defaults) < (len(self.args) - len(other.args)):
      return 'extranous positional arguments do not have default values '\
        '(extranous arguments are {0!r})'.format(self.args[len(other.args):])

    # Check varargs/kwargs.
    if self.varargs is None and other.varargs is not None:
      return 'does not implement varargs'
    if self.varkw is None and other.varkw is not None:
      return 'does not implement varkw'

    # Check kwonlyargs.
    a = set(self.kwonlyargs)
    b = set(other.kwonlyargs)
    if not b.issubset(a):
      return 'missing kwonlyargs ({0!r})'.format(b - a)

    # Check kwonlydefaults.
    missing_defaults = set(k for k in other.kwonlydefaults if k not in self.kwonlydefaults)
    if missing_defaults:
      return 'missing kwonlydefaults ({0!r})'.format(missing_defaults)

    return None


class Decoration(object):
  """
  A wrapper for functions decorated with one of the decorators of this module.
  Using this wrapper class has two main advantages:
  - Trying to decorate staticmethod/classmethod in the "wrong order" results
    in an error (they won't accept an instance of this class)
  - Decorating staticmethod/classmethod works in Python 2 due to this wrapper
    class
  """

  def __init__(self, func):
    self.func = func
    self.is_default = False
    self.is_final = False
    self.is_override = False
    self.is_optional = False
    self.skip = False

  @classmethod
  def wraps(cls, **set_members):
    def decorator(func):
      return cls.wrap(func, **set_members)
    return decorator

  @classmethod
  def wrap(cls, func, **set_members):
    if not isinstance(func, cls):
      func = cls(func)
    for key, value in six.iteritems(set_members):
      if not hasattr(func, key):
        raise AttributeError('{0}.{1}'.format(cls.__name__, key))
      setattr(func, key, value)
    return func

  @classmethod
  def unwrap(cls, func):
    if isinstance(func, cls):
      return func.func
    return func

  @classmethod
  def split(cls, func):
    decoration = cls.wrap(func)
    return decoration, decoration.func


class _Member(object):

  def __init__(self, interface, name, hidden=False):
    self.interface = interface
    self.name = name
    self.hidden = hidden

  def __repr__(self):
    result = '<{0} {1!r}'.format(type(self).__name__, self.name)
    if self.interface:
      result += ' of interface {0!r}'.format(self.interface.__name__)
    return result + '>'

  @property
  def is_bound(self):
    if self.interface and self.name:
      return True
    return False

  @property
  def required(self):
    raise NotImplementedError


class Method(_Member):
  """
  Represents a method on an interface. A method is considered static if it is
  a [[classmethod]] or [[staticmethod]].

  *Changed in 0.0.2*: Added *original* argument and member.
  """

  def __init__(self, interface, name, argspec, default=None, final=False,
               hidden=False, static=False, optional=False, original=None):
    super(Method, self).__init__(interface, name)
    self.argspec = argspec
    self.default = default
    self.final = final
    self.hidden = hidden
    self.static = static
    self.optional = optional
    self.original = original

  def __repr__(self):
    s = super(Method, self).__repr__()[1:]
    if self.static:
      s = 'static ' + s
    if self.hidden:
      s = 'hidden ' + s
    if self.final:
      s = 'final ' + s
    return '<' + s

  def __call__(self, *a, **kw):
    if self.default:
      return self.default(*a, **kw)
    return None

  def __eq__(self, other):
    if type(other) == type(self):
      return (self.argspec, self.final, self.hidden, self.static) == \
        (other.argspec, other.final, other.hidden, other.static)
    return False

  def __ne__(self, other):
    return not (self == other)

  @property
  def required(self):
    return self.default is None

  @classmethod
  def is_candidate(cls, name, value):
    if name.startswith('_') and not name.endswith('_'):  # Private function
      return False
    props, value = Decoration.split(value)
    if props.skip:
      return False
    if not isinstance(value, (types.FunctionType, staticmethod, classmethod)):
      return False
    return True

  @classmethod
  def wrap_candidate(cls, interface, name, value):
    if cls.is_candidate(name, value):
      # We don't want these functions to be an actual "member" of the interface
      # API as they can be implemented for every interface and not collide.
      hidden = name in ('__new__', '__init__', '__constructed__')
      props, value = Decoration.split(value)
      # If it's one of the hidden methods, they also act as the "default"
      # implementation because we actually want to call them independently
      # of potential overrides by the implementation.
      default = value if props.is_default or hidden else None
      static = isinstance(value, (staticmethod, classmethod))
      spec = FunctionSpec.from_function(value)
      return Method(
        interface,
        name,
        spec,
        default,
        props.is_final,
        hidden,
        static,
        props.is_optional,
        value)
    return None


class Attribute(_Member):
  """
  Represents an attribute on an interface. Note that attributes on interface
  can conflict the same way methods can do. Usually, attribute declaratons
  are only used if the interface adds the respective member in `__init__()`.

  Inside an interface declaration, use the #attr() function to create an
  attribute that will be bound automatically when the interface class is
  constructed.

  *Changed in 2.5.0*: Added *default* argument and member.
  *Changed in 2.5.0*: Added *static* argument and member.
  """

  def __init__(self, interface, name, type=None, default=NotSet, static=False):
    super(Attribute, self).__init__(interface, name)
    self.type = type
    self.default = default
    self.static = static

  def __repr__(self):
    s = super(Attribute, self).__repr__()[1:]
    if self.static:
      s = 'static ' + s
    return '<' + s

  def make_default(self):
    if self.default is NotSet:
      raise RuntimeError('Attribute.default is NotSet')
    if callable(self.default):
      return self.default()
    return self.default

  @property
  def required(self):
    return self.default is NotSet


class Property(_Member):
  """
  Represents a property in an interface. A property can have default
  implementations for the getter, setter and deleter independently.
  """

  def __init__(self, interface, name, getter_impl=None, setter_impl=NotImplemented,
               deleter_impl=NotImplemented, getter_final=False, setter_final=False,
               deleter_final=False):
    super(Property, self).__init__(interface, name)
    self.getter_impl = getter_impl
    self.setter_impl = setter_impl
    self.deleter_impl = deleter_impl
    self.getter_final = getter_final
    self.setter_final = setter_final
    self.deleter_final = deleter_final

  def is_pure_default(self):
    return all(x is not None for x in [self.getter_impl, self.setter_impl, self.deleter_impl])

  def satisfy(self, value):
    assert isinstance(value, property), type(value)
    if value.fget and self.getter_final:
      raise ValueError('property {0}: getter must not be implemented'.format(self.name))
    if value.fset and self.setter_final:
      raise ValueError('property {0}: setter must not be implemented'.format(self.name))
    if value.fdel and self.deleter_final:
      raise ValueError('property {0}: deleter must not be implemented'.format(self.name))
    if self.getter_impl is None and not value.fget:
      raise ValueError('property {0}: missing getter'.format(self.name))
    if self.setter_impl is None and not value.fset:
      raise ValueError('property {0}: missing setter'.format(self.name))
    if self.deleter_impl is None and not value.fdel:
      raise ValueError('property {0}: missing deleter'.format(self.name))

    getter, setter, deleter = value.fget, value.fset, value.fdel
    if not getter and self.getter_impl not in (None, NotImplemented):
      getter = self.getter_impl
    if not setter and self.setter_impl not in (None, NotImplemented):
      setter = self.setter_impl
    if not deleter and self.deleter_impl not in (None, NotImplemented):
      deleter = self.deleter_impl

    return property(getter, setter, deleter)

  @property
  def required(self):
    # TODO (@NiklasRosenstein): Not so sure about this logic tbh.
    return not all(self.getter_impl, self.setter_impl, self.deleter_impl)

  @property
  def getter(self):
    return property().getter

  @property
  def setter(self):
    return property().setter

  @property
  def deleter(self):
    return property().deleter

  @classmethod
  def is_candidate(cls, name, value):
    return isinstance(value, property)

  @classmethod
  def wrap_candidate(cls, interface, name, value):
    if cls.is_candidate(name, value):
      return Property.from_python_property(interface, name, value)
    return None

  @classmethod
  def from_python_property(cls, interface, name, value):
    assert isinstance(value, property), type(value)
    if Decoration.wrap(value.fget).is_default:
      getter = Decoration.unwrap(value.fget)
    else:
      getter = None
    if Decoration.wrap(value.fset).is_default:
      setter = Decoration.unwrap(value.fset)
    elif value.fset:
      setter = None
    else:
      setter = NotImplemented
    if Decoration.wrap(value.fdel).is_default:
      deleter = Decoration.unwrap(value.fdel)
    elif value.fdel:
      deleter = None
    else:
      deleter = NotImplemented
    return cls(
      interface,
      name,
      getter,
      setter,
      deleter,
      Decoration.wrap(value.fget).is_final,
      Decoration.wrap(value.fset).is_final,
      Decoration.wrap(value.fdel).is_final)


class InterfaceClass(type):
  """
  The class for interfaces. Interfaces allow mapping-like access to their
  members.
  """

  def __new__(cls, name, bases, attrs):
    members = {}

    for base in bases:
      if isinstance(base, InterfaceClass):
        members.update(base.__members)

    # Convert function declarations in the class to Method objects and
    # bind Attribute objects to the new interface class.
    for key, value in six.iteritems(attrs):
      member = None
      if isinstance(value, _Member) and not value.is_bound:
        value.name = key
        member = value
      if member is None:
        member = Method.wrap_candidate(None, key, value)
      if member is None:
        member = Property.wrap_candidate(None, key, value)
      if member is not None:
        members[key] = member
        continue
      if isinstance(value, Decoration) and value.skip:
        attrs[key] = value.func

    for key, attr in six.iteritems(members):
      if key in attrs:
        del attrs[key]
      if isinstance(attr, Attribute) and attr.static and \
          not any(hasattr(x, key) for x in bases):
        attrs[key] = attr.make_default()

    self = type.__new__(cls, name, bases, attrs)
    self.__implementations = OrderedSet()
    self.__members = members

    for key, value in six.iteritems(members):
      value.interface = self

    return self

  def __len__(self):
    return len(self.__members)

  def __contains__(self, key):
    return key in self.__members

  def __getitem__(self, key):
    return self.__members[key]

  def __iter__(self):
    return iter(self.__members)

  def __instancecheck__(self, instance):
    if issubclass(type(instance), self):
      return True
    return self.provided_by(instance)

  def get(self, key, default=None):
    return self.__members.get(key, default)

  def members(self, include_hidden=False):
    for member in six.itervalues(self.__members):
      if include_hidden or not member.hidden:
        yield member

  def implemented_by(self, x):
    if not isinstance(x, type):
      raise TypeError('expected type, got {0}'.format(type(x).__name__))
    if not issubclass(x, Implementation):
      return False
    for interface in x.__implements__:
      if issubclass(interface, self):
        return True
    return False

  def provided_by(self, x):
    if not isinstance(x, Implementation):
      return False
    return self.implemented_by(type(x))

  def implementations(self):
    return iter(self.__implementations)


class Interface(six.with_metaclass(InterfaceClass)):
  """
  Base class for interfaces. Interfaces can be directly instantiated if all
  required members are passed as keyword arguments to its constructor. Methods
  passed into the #Interface constructor like this will not receive a *self*
  argument.
  """

  @Decoration.wraps(skip=True)
  def __new__(cls, *args, **kwargs):
    """ Constructs an instance of the interface from the specified arguments.
    All required members of an interface must be satisfied with the specified
    arguments. Interfaces with only a single required member can be created
    with a single positional argument. Interfaces with more than one required
    member need to be instantiated with keyword arguments only.

    We call this method of creating an interface instance "lambda
    instantiation". """

    cache = getattr(cls, '_Interface__construct_cache', None)
    if cache is None:
      cache = cls._Interface__construct_cache = {}

    lambda_type = getattr(cls, '_Interface__lambda_type', None)
    if lambda_type is None:
      class lambda_type(Implementation):
        __implements__ = [cls]
        __required_members = frozenset(x.name for x in cls.members() if x.required)
        __all_members = frozenset(x.name for x in cls.members())

        def __init__(self, *args, **kwargs):
          if args:
            if len(self.__required_members) > 1:
              raise TypeError('{0} has more than one non-default member and thus '
                              'must be constructed from keyword arguments only.'
                              .format(cls.__name__))
            kwargs[next(iter(self.__required_members))] = args[0]

          given = frozenset(kwargs.keys())
          missing = self.__required_members - given
          if missing:
            raise TypeError('missing keyword argument "{0}"'.format(next(iter(missing))))
          extra = given - self.__all_members
          if extra:
            raise TypeError('extranous keyword argument "{0}"'.format(next(iter(extra))))

          # Wrap functions as static methods.
          for key, value in six.iteritems(kwargs):
            # TODO: Type checking
            setattr(self, key, value)

        # Need to provide the members for InterfaceClass, but we want it
        # to skip the type checking.
        locals().update(dict((k, _NoCheckType) for k in __required_members))

      lambda_type.__name__ = cls.__name__
      lambda_type.__qualname__ = cls.__name__
      cls._Interface__lambda_type = lambda_type

    return lambda_type(*args, **kwargs)


def is_interface(obj):
  return isinstance(obj, type) and issubclass(obj, Interface)


def get_conflicting_members(a, b):
  """
  Returns a set of members that are conflicting between the two interfaces
  *a* and *b*. If the interfaces have no incompatible members, an empty set
  is returned and both interfaces can be implemented in the same
  implementation.
  """

  if not is_interface(a) or not is_interface(b):
    raise TypeError('expected Interface subclass')
  if issubclass(a, b) or issubclass(b, a):
    return set()

  conflicts = []
  for am in a.members():
    try:
      bm = b[am.name]
    except KeyError:
      continue
    if am != bm:
      conflicts.append(am.name)

  return conflicts


def check_conflicting_interfaces(interfaces):
  """
  Raises a #ConflictingInterfacesError if any of the specified interfaces
  have conflicting members.
  """

  for x in interfaces:
    if not is_interface(x):
      raise TypeError('expected Interface subclass')
    for y in interfaces:
      if x is not y and get_conflicting_members(x, y):
        raise ConflictingInterfacesError(x, y)


def reduce_interfaces(interfaces):
  """
  Reduces a list of interfaces eliminating classes that are parents of
  other classes in the list.
  """

  result = []
  for interface in interfaces:
    if not isinstance(interface, type):
      raise TypeError('expected Type, got {0}'.format(type(interface).__name__))
    skip = False

    for i in range(len(result)):
      if issubclass(interface, result[i]):
        result[i] = interface
        skip = True
        break
      if issubclass(result[i], interface):
        skip = True
        break

    if not skip:
      result.append(interface)

  return result


class ImplementationError(RuntimeError):

  def __init__(self, impl, interfaces=(), errors=()):
    self.impl = impl
    self.interfaces = list(interfaces)
    self.errors = list(errors)

  def add(self, interface, message):
    if interface and interface not in self.interfaces:
      self.interfaces.append(interface)
    if message not in self.errors:
      self.errors.append(message)

  def __str__(self):
    lines = []
    lines.append(
      "'{0}' does not meet requirements of interface{1} {2}"
      .format(
        self.impl.__name__,
        '' if len(self.interfaces) == 1 else 's',
        self.interfaces[0].__name__ if len(self.interfaces) == 1 else
          ('{' + ', '.join(repr(x.__name__) for x in self.interfaces) + '}'),  # pylint: disable=C0330
      )
    )
    lines += ['  - {0}'.format(x) for x in self.errors]
    return '\n'.join(lines)


class Implementation(InlineMetaclassBase):
  """
  Parent for classes that implement one or more interfaces.
  """

  def __metanew__(cls, name, bases, attrs):
    implements = []
    if bases != (InlineMetaclassBase,):  # Subclass of Implementation
      for base in bases:
        if issubclass(base, Implementation):
          for interface in base.__implements__:
            if interface not in implements:
              implements.append(interface)

    for interface in attrs.get('__implements__', []):
      if interface not in implements:
        implements.append(interface)

    implements = reduce_interfaces(implements)
    check_conflicting_interfaces(implements)
    attrs['__implements__'] = implements

    def has_member(member_name):
      if member_name in attrs:
        return True
      for base in bases:
        if hasattr(base, member_name) and getattr(base, member_name) != getattr(object, member_name, None):
          return True
      return False

    # Assign default implementations and static attributes.
    for interface in implements:
      for member in interface.members():
        if isinstance(member, Method) and not has_member(member.name) and member.default:
          attrs[member.name] = member.default
        elif (isinstance(member, Attribute) and member.static and
              member.default is not NotSet and not has_member(member.name) and
              not any(hasattr(x, member.name) for x in bases)):
          attrs[member.name] = member.make_default()

    self = type.__new__(cls, name, bases, attrs)
    impl_error = ImplementationError(self)

    # Unwrap all [[Decoration]] members and validate the is_override
    # decoration.
    for key, value in vars(self).items():
      if not isinstance(value, Decoration) or not value.is_override:
        continue
      for interface in implements:
        if key in interface:
          break
      else:
        impl_error.add(None, "'{0}' does not override a method of any of "
                             "the implemented interfaces.".format(key))
      setattr(self, key, value.func)  # unpack the Decoration

    # Ensure all interface members are satisfied.
    for interface in implements:
      for member in interface.members():
        value = getattr(self, member.name, NotSet)
        if value is _NoCheckType:  # Internal for Interface.__new__()
          continue
        if isinstance(member, Method):
          if isinstance(value, types.MethodType):
            value = value.im_func if six.PY2 else value.__func__
          if member.final and value is not NotSet and member.default != value:
            impl_error.add(interface, 'implemented final method: {0}()'.format(member.name))
            continue
          if value is NotSet:
            if not member.optional:
              impl_error.add(interface, 'missing method: {0}()'.format(member.name))
          elif not isinstance(value, (types.FunctionType, types.MethodType)):
            impl_error.add(interface, 'expected method, got {0}: {1}()'.format(
              type(value).__name__, member.name))
        elif isinstance(member, Property):
          if not hasattr(self, member.name):
            if not member.is_pure_default():
              impl_error.add(interface, 'missing property: {0}'.format(member.name))
          elif not isinstance(value, property):
            impl_error.add(interface, 'expected property, got {0}: {1}'.format(
              type(value).__name__, member.name))
          else:
            try:
              value = member.satisfy(value)
            except ValueError as exc:
              impl_error.add(interface, str(exc))
            else:
              setattr(self, member.name, value)

    if impl_error.errors:
      raise impl_error

    # The implementation is created successfully, add it to the
    # implementations set of all interfaces and their parents.
    for interface in implements:
      bases = [interface]
      while bases:
        new_bases = []
        for x in bases:
          if issubclass(x, Interface):
            x._InterfaceClass__implementations.add(self)
          new_bases += x.__bases__
        bases = new_bases

    return self

  def __init__(self):
    for interface in self.__implements__:
      for member in interface.members():
        if isinstance(member, Attribute) and not member.static and member.default is not NotSet:
          setattr(self, member.name, member.make_default())
      member = interface.get('__init__')
      if member:
        member.default(self)
    for interface in self.__implements__:
      member = interface.get('__constructed__')
      if member:
        member.default(self)


class ConflictingInterfacesError(RuntimeError):

  def __init__(self, a, b):
    self.a = a
    self.b = b

  def __str__(self):
    lines = ["'{0}' conflicts with '{1}'".format(self.a.__name__, self.b.__name__)]
    for member in get_conflicting_members(self.a, self.b):
      lines.append('  - {0}'.format(member))
    return '\n'.join(lines)


def implements(*interfaces, **kwargs):
  """
  Decorator for a class to mark it as implementing the specified *interfaces*.
  Note that this will effectively create a copy of the wrapped class that
  inherits from the #Implementation class.
  """

  resolve_metaclass_conflict = kwargs.pop('resolve_metaclass_conflict', True)
  for key in kwargs:
    raise TypeError('unexpected keyword argument {0}'.format(key))

  def decorator(cls):
    if cls.__bases__ == (object,):
      bases = (Implementation,)
    else:
      bases = cls.__bases__ + (Implementation,)
    return copy_class(cls, bases, update_attrs={'__implements__': interfaces},
      resolve_metaclass_conflict=resolve_metaclass_conflict)

  return decorator


def attr(type=None, default=NotSet, static=False):
  """
  Declare an unnamed attribute that will be bound when the interface is
  constructed. The result of this function must be assigned to a member
  on the class-level of an #Interface declaration.

  *default* can be a callable, in which case it is called at the time
  the default value is needed, or an arbitrary value.

  *Changed in 2.5.0*: Added *default* parameter.
  """

  return Attribute(None, None, type, default, static)


def staticattr(value):
  """
  Assign a static attribute to the interface. This static attribute will carry
  over the implementation class.

  *value* can be a callable, in which case it is called at the time
  the default value is needed, or an arbitrary value.

  *Changed in 2.4.0*: Added. \\
  *Changed in 2.5.0*: Now returns an [[Attribute]] instance of a
  `StaticAttribute` instance.
  """

  return Attribute(None, None, None, value, True)


def default(func):
  """
  Decorator for interface methods to mark them as a default implementation.
  """

  return Decoration.wrap(func, is_default=True)


def final(func):
  """
  Decorator for an interface method or property component to mark it as a
  default implementation and that it may not actually be implemented.
  """

  return Decoration.wrap(func, is_default=True, is_final=True)


def override(func):
  """
  Marks a function as expected override a method in an implemented interface.
  If the function does not override a method in an implemented interface,
  a #RuntimeError will be raised when the #Implementation subclass is created.

  Using #override() implies #default().
  """

  return Decoration.wrap(func, is_override=True)


def overrides(interface):
  """
  Same as #override() but you must specify the interface that the decorated
  method overrides a member of.
  """

  def decorator(func):
    return override(func)

  return decorator


def optional(func):
  """ Decorator for functions to indicate that the interface member is optional
  and is not required to be available on implementations of the interface. """

  return Decoration.wrap(func, is_optional=True)
