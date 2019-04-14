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

from .meta import InlineMetaclassBase
from six import iteritems
from six.moves import zip

import types
import six


class Constructor(object):
  """
  Represents a Constructor for a sumtype.

  # Attributes

  name (str): Name of the constructor. Automatically assigned when the
    #Sumtype is constructed.
  type (type): The #Sumtype subclass that this constructor belongs to.
  args (tuple): The arguments that the #Constructor was created with.
  members (dict): A dictionary of members that only belong to this
    #Constructor object (usually added with the #member_of decorator).
  """

  def __init__(self, *args):
    self.name = None
    self.type = None
    self.args = args
    self.members = {}

  def bind(self, type, name):
    obj = Constructor(*self.args)
    obj.type = type
    obj.name = name
    obj.members = self.members.copy()
    return obj

  def accept_args(self, *args):
    if self.type is None or self.name is None:
      raise RuntimeError('unbound Constructor')
    if len(args) != len(self.args):
      raise TypeError('{}.{}() expected {} arguments, got {}'.format(
        self.type.__name__, self.name, len(self.args), len(args)))
    return dict(zip(self.args, args))

  def __call__(self, *args):
    if self.type is None or self.name is None:
      raise RuntimeError('unbound Constructor')
    return self.type(self, self.accept_args(*args))


class member_of(object):
  """
  A decorator for functions or values that are supposed to be members of
  only a specific sumtype's constructor (or multiple constructors). Instances
  of this class will be automatically unpacked by the :class:`_SumtypeMeta`
  constructor and moved into the :attr:`Constructor.members` dictionary.
  """

  def __init__(self, constructors=None, value=None, name=None):
    if isinstance(constructors, Constructor):
      constructors = [constructors]
    self.constructors = constructors
    self.value = value
    self.name = name

    if name:
      for c in constructors:
        c.members[name] = value

  def __call__(self, value):
    if not self.name:
      self.name = value.__name__
    for c in self.constructors:
      c.members[self.name] = value
    return self

  def update_constructors(self, attrname):
    for constructor in self.constructors:
      constructor.members[attrname] = self.value


class Sumtype(InlineMetaclassBase):
  """
  Base class for sumtypes. You can access all members of the sumtype
  module via this type (but not through subclasses).

  ```python
  from nr.types import sumtype

  class Result(sumtype):
    Ok = sumtype.constructor()
    Error = sumtype.constructor('message')

  assert not hasattr(Result, 'constructor')
  ```
  """

  __addins__ = []
  __constructors__ = {}

  def __metanew__(cls, name, bases, attrs):
    subtype = type.__new__(cls, name, bases, attrs)

    # Get all previous constructors and get all new ones.
    constructors = getattr(subtype, '__constructors__', {}).copy()
    for key, value in iteritems(vars(subtype)):
      if isinstance(value, Constructor):
        constructors[key] = value

    # Update constructors from member_of declarations.
    for key, value in list(iteritems(vars(subtype))):
      if isinstance(value, member_of):
        delattr(subtype, key)

    # Bind constructors.
    for key, value in iteritems(constructors):
      setattr(subtype, key, value.bind(subtype, key))
    subtype.__constructors__ = constructors

    # Invoke addons.
    for addin in getattr(subtype, '__addins__', []):
      addin(subtype)

    return subtype

  def __init__(self, constructor, attrs):
    assert isinstance(constructor, Constructor), type(constructor)
    assert isinstance(attrs, dict), type(attrs)
    self.__constructor__ = constructor
    for key, value in iteritems(constructor.members):
      if isinstance(value, types.FunctionType):
        value = value.__get__(self, constructor.type)
      setattr(self, key, value)
    for key in constructor.args:
      if key not in attrs:
        raise ValueError('missing key in attrs: {!r}'.format(key))
    for key, value in iteritems(attrs):
      if key not in constructor.args:
        raise ValueError('unexpected key in attrs: {!r}'.format(key))
      setattr(self, key, value)

  def __getitem__(self, index):
    if hasattr(index, '__index__'):
      index = index.__index__()
    if isinstance(index, int):
      return getattr(self, self.__constructor__.args[index])
    elif isinstance(index, slice):
      return tuple(getattr(self, k) for k in self.__constructor__.args[index])
    else:
      raise TypeError('indices must be integers or slices, not str')

  def __iter__(self):
    for k in self.__constructor__.args:
      yield getattr(self, k)

  def __len__(self):
    return len(self.__constructor__.args)

  def __repr__(self):
    return '{}.{}({})'.format(type(self).__name__, self.__constructor__.name,
      ', '.join('{}={!r}'.format(k, getattr(self, k)) for k in self.__constructor__.args))

  def __eq__(self, other):
    if type(self) != type(other): return False
    if self.__constructor__ != other.__constructor__: return False
    for key in self.__constructor__.args:
      if getattr(self, key) != getattr(other, key): return False
    return True

  def __ne__(self, other):
    return not (self == other)


def add_is_methods(type):
  """
  A sumtype add-in that adds an `is_...()` methods for every constructor.
  """

  import re

  def create_is_check(func_name, constructor_name):
    def check(self):
      constructor = getattr(self, constructor_name)
      return self.__constructor__ == constructor
    check.__name__ = name
    check.__qualname__ = name
    return check
  for name in type.__constructors__.keys():
    func_name = 'is_' + '_'.join(re.findall('[A-Z]+[^A-Z]*', name)).lower()
    setattr(type, func_name, create_is_check(func_name, name))


Sumtype.constructor = Constructor
Sumtype.member_of = member_of
Sumtype.add_is_methods = add_is_methods
Sumtype.__addins__.append(add_is_methods)

import sys
Sumtype.__module_object__ = sys.modules[__name__]  # keep explicit reference for Py2
sys.modules[__name__] = Sumtype
