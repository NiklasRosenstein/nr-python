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

"""
Offers the ability to implement sumtypes in Python, a concept borrowed from
functional programming languages.
"""

from nr.types.meta import InlineMetaclassBase
from nr.types.structured import Object, Field, FieldSpec, create_object_class
from .meta import InlineMetaclassBase
from six import iteritems
from six.moves import zip

import types
import six


class Constructor(object):
  """
  Represents a constructor for a sumtype. Constructors basically wrap an
  [[Object]]. Constructors are declared as class-level members of a
  [[Sumtype]] subclass.
  """

  def __init__(self, *args, **kwargs):
    """
    Creates a new constructor object.

    # Arguments (1)

    object_cls (type)

    # Arguments (2)

    fields (dict, list, str)
    mixins (tuple)

    # Arguments (3)

    args (tuple of (str, Field))
    mixins (tuple)

    # Parameters:

    object_cls: An [[Object]] subclass.
    fields: Fields for a new object class. If a string is specified, it will
      be split by whitespace or commas to generate the list version. If a list
      is specified, every member will be turned into a [[Field]] accepting any
      Python object. A dictionary will be treated as the members of an
      [[Object]] subclass.
    mixins: The mixins for creating the Object class.
    """

    def raise_kwargs():
      for key in kwargs:
        raise TypeError('unexpected keyword argument {!r}'.format(key))

    def build_fields(field_names):
      return {name: Field(object) for name in field_names}

    if len(args) == 1 and isinstance(args[0], type):  # NOTE: constructor 1
      raise_kwargs()
      object_cls = args[0]
      if not issubclass(object_cls, Object):
        raise TypeError('expected Object subclass')

    elif len(args) == 1 and isinstance(args[0], (dict, list, str)):  # NOTE: constructor 2
      mixins = kwargs.pop('mixins', ())
      raise_kwargs()
      value = args[0]
      if isinstance(value, str):
        if ',' in value:
          fields = build_fields(x.strip() for x in value.split(','))
        else:
          fields = build_fields(value.split())
      elif isinstance(value, list):
        fields = build_fields(value)
      object_cls = create_object_class('_Temporary', fields, mixins=mixins)

    else:  # NOTE: constructor 3
      mixins = kwargs.pop('mixins', ())
      raise_kwargs()
      fields = build_fields(args)
      object_cls = create_object_class('_Temporary', fields, mixins=mixins)

    self.object_cls = object_cls

  def add_member(self, name, value):
    setattr(self.object_cls, name, value)

  def bind(self, name, sumtype):
    """
    Binds the [[Constructor]] to the [[Sumtype]] class. It basically just
    rebuilds the [[#object_cls]] class to be a subclass of the *sumtype*.
    """

    name = sumtype.__name__ + '.' + name
    attrs = {'__skip_sumtype_meta__': True}
    typ = type(name, (sumtype, self.object_cls), attrs)
    typ.__constructor__ = self
    return typ


class member_of(object):
  """
  A decorator for functions or values that are supposed to be members of
  only a specific sumtype's constructor (or multiple constructors). Instances
  of this class will be automatically unpacked by the [[_SumtypeMeta]]
  constructor and moved into the [[Constructor.members]] dictionary.
  """

  def __init__(self, constructors=None, value=None, name=None):
    if isinstance(constructors, Constructor):
      constructors = [constructors]
    if any(not isinstance(x, Constructor) for x in constructors):
      raise TypeError('expected Constructor objects', constructors)
    self.constructors = constructors
    self.value = value
    self.name = name
    if self.name:
      self._propagate()

  def __call__(self, value):
    if self.name:
      raise RuntimeError('member_of.name already set')
    self.name = value.__name__
    self.value = value
    self._propagate()
    return self

  def _propagate(self):
    assert self.name
    for c in self.constructors:
      c.add_member(self.name, self.value)


class _SumtypeMeta(type(Object)):

  def __new__(cls, name, bases, attrs):
    subtype = super(_SumtypeMeta, cls).__new__(cls, name, bases, attrs)
    if attrs.get('__skip_sumtype_meta__', False):
      return subtype

    subtype.__fields__ = FieldSpec([])

    # Get all previous constructors and get all new ones.
    constructors = getattr(subtype, '__constructors__', {}).copy()
    default_constructor = None
    for key, value in iteritems(vars(subtype)):
      if isinstance(value, Constructor):
        if key == '__default__':
          default_constructor = value
        else:
          value.name = key
          constructors[key] = value

    # Update constructors from member_of declarations.
    for key, value in list(iteritems(vars(subtype))):
      if isinstance(value, member_of):
        delattr(subtype, key)

    # Bind constructors.
    for key, value in iteritems(constructors):
      setattr(subtype, key, value.bind(key, subtype))
    subtype.__constructors__ = constructors
    if default_constructor:
      assert default_constructor.name
      subtype.__default__ = default_constructor.name
    if hasattr(subtype, '__default__') and not isinstance(subtype.__default__, str):
      raise TypeError('{}.__default__ must be a str, got value {}'
                      .format(subtype.__name__, subtype.__default__))

    # Invoke addons.
    for addin in getattr(subtype, '__addins__', []):
      addin(subtype)

    return subtype

  def __instancecheck__(self, inst):
    if issubclass(type(inst), self) or getattr(inst, '__sumtype__') == self:
      return True
    return False


@six.add_metaclass(_SumtypeMeta)
class Sumtype(object):
  """
  Base class for sumtypes. Subclass and created [[Constructor]] objects at
  the class-level.

  A `__default__` constructor may be specified which is created when
  instantiating an instance of the [[Sumtype]] directly. The `__default__`
  may be set to a [[Constructor]] instance or to the name of a constructor.
  Note that the `__default__` is not handled on subclasses.
  """

  __addins__ = []
  __constructors__ = {}

  def __new__(cls, *args, **kwargs):
    if hasattr(cls, '__constructor__'):
      # This is acually trying to construct from a constructor.
      assert issubclass(cls, Object)
      obj = object.__new__(cls)
      obj.__init__(*args, **kwargs)
      return obj

    if '__default__' in vars(cls):  # Don't inherit __default__
      constructor = getattr(cls, cls.__default__)
      return constructor(*args, **kwargs)

    constructors = ','.join(x for x in cls.__constructors__ if not x.startswith('_'))
    raise TypeError('cannot construct sumtype {!r}, use any of its '
                    'constructors instead: {{{}}}'
                    .format(cls.__name__, constructors))


def add_is_methods(sumtype):
  """
  A sumtype add-in that adds an `is_...()` methods for every constructor.
  """

  import re

  def create_is_check(func_name, constructor_name):
    def check(self):
      return type(self) == getattr(self, constructor_name)
    check.__name__ = func_name
    check.__qualname__ = func_name
    return check

  for name in sumtype.__constructors__.keys():
    func_name = 'is_' + '_'.join(re.findall('[A-Z]+[^A-Z]*', name)).lower()
    setattr(sumtype, func_name, create_is_check(func_name, name))


Sumtype.__addins__.append(add_is_methods)
