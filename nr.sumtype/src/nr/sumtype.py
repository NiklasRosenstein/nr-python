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

from __future__ import absolute_import
from nr.metaclass.copy import copy_class
from nr.metaclass.inline import InlineMetaclassBase
from nr.stream import Stream
import collections
import re

__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
__version__ = '0.0.4'


def _merge_dicts(*dicts):
  result = {}
  [result.update(x) for x in dicts]
  return result


class _RemoveMe(object):
  def __init__(self, value):
    self.value = value
  @classmethod
  def wrap(cls, value):
    return value if isinstance(value, cls) else cls(value)
  @classmethod
  def unwrap(cls, value):
    return value.value if isinstance(value, cls) else value


class BaseConstructor(object):
  """ A constructor is created at the class-level of a #Sumtype subclass to
  create a member constructor. When the #Sumtype subclass is created,
  #BaseConstructor.create_type() is called in order to produce a subclass
  of the #Sumtype that can be instantiated for its member. """

  def create_type(self, sumtype, name):
    raise NotImplementedError


class Constructor(BaseConstructor):
  """ The standard constructor class.

  If *fields* is a string or list of strings, it will be used to create a
  namedtuple type. Otherwise, *fields* must be a type object. """

  def __init__(self, fields=()):
    self._fields = fields
    self._members = {}

  def member(self, func):
    self._members[func.__name__] = _RemoveMe.unwrap(func)
    return _RemoveMe.wrap(func)

  def add_member(self, name, data):
    self._members[name] = data

  def create_type(self, sumtype, name, add_attrs):
    if isinstance(self._fields, (list, tuple, str)):
      btype = collections.namedtuple(name, self._fields)
    else:
      btype = self._fields

    qualname = sumtype.__qualname__ + '.' + name if hasattr(sumtype, '__qualname__') else None
    name = sumtype.__name__ + '.' + name

    if btype.__new__ == object.__new__:
      # If __new__ is not overwritten in the class, it will fall back to
      # Sumtype.__new__(), which will cause an infinite recursion when
      # creating an instance of the constructor.
      def __new__(cls, *args, **kwargs):
        self = object.__new__(cls)
        self.__init__(*args, **kwargs)
        return self
      add_attrs = add_attrs.copy()
      add_attrs['__new__'] = __new__

    return copy_class(
      btype,
      btype.__bases__ + (sumtype,),
      new_name=name,
      new_qualname=qualname,
      module=sumtype.__module__,
      update_attrs=_merge_dicts(add_attrs, self._members),
      resolve_metaclass_conflict=True,
      reduce_mro=True)


class Sumtype(InlineMetaclassBase):
  """ Base class for sumtypes. #BaseConstructor instances must be created at
  class-level to define the sumtype's members. """

  def __metainit__(cls, name, bases, attrs):
    # Constructors create a subclass for the constructor type, which will
    # cause them to meta-initialize as well. Ignore constructor types via
    # this attribute.
    SKIP_ATTR = ' _Sumtype__skip_sumtype_meta'
    if attrs.get(SKIP_ATTR):
      return
    add_attrs = {SKIP_ATTR: True}

    # Inherit parent class constructors.
    cls.__constructors__ = Stream(bases)\
      .map(lambda x: getattr(x, '__constructors__', {}))\
      .reduce(lambda a, b: _merge_dicts(a, b), initial={})

    # Find all constructors defined in the class.
    cls.__constructors__.update(Stream(vars(cls).items())\
      .filter(lambda x: isinstance(x[1], BaseConstructor))\
      .filter(lambda x: x[0] != '__default__')\
      .collect(dict))

    # Create constructor types (name -> Constructor)
    constructor_types = Stream(cls.__constructors__.items())\
      .map(lambda x: (x[0], x[1].create_type(cls, x[0], add_attrs)))\
      .collect(dict)

    # Translate the default constructor to a string reference, if any.
    default = getattr(cls, '__default__', None)
    if default is None:
      cls.__default__ = None
    else:
      if not isinstance(default, str):
        try:
          default = Stream(vars(cls).items())\
            .filter(lambda x: x[0] != '__default__' and x[1] is default)\
            .next()[0]
          if default not in constructor_types:
            raise StopIteration
        except StopIteration:
          raise ValueError('{}.default = {!r} is not a constructor of '
            'this sumtype.'.format(cls.__name__, default))
      cls.__default__ = default

    # Populate the class with the constructor types.
    for key, value in constructor_types.items():
      setattr(cls, key, value)

    # Remove unwanted attributes.
    for key in dir(cls):
      value = getattr(cls, key)
      if isinstance(value, _RemoveMe):
        delattr(cls, key)

  def __new__(cls, *args, **kwargs):
    if cls.__default__ is None:
      constructors = ','.join(x for x in cls.__constructors__
        if not x.startswith('_'))
      raise TypeError('cannot directly construct sumtype {!r}, use one of '
                      'its constructors instead: {{{}}}'
                      .format(cls.__name__, constructors))
    return getattr(cls, cls.__default__)(*args, **kwargs)


def add_constructor_tests(sumtype):
  """ Adds methods to the *sumtype* to test if an instance of the sumtype
  belongs to a certain constructor. """

  def create_is_check(func_name, constructor_name):
    def check(self):
      return type(self) == getattr(self, constructor_name)
    check.__name__ = func_name
    check.__qualname__ = func_name
    return check

  for name in sumtype.__constructors__.keys():
    func_name = 'is_' + '_'.join(re.findall('[A-Z]+[^A-Z]*', name)).lower()
    setattr(sumtype, func_name, create_is_check(func_name, name))

  return sumtype
