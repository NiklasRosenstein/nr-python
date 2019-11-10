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

from nr.types.stream import chain, unique


def get_staticmethod_func(cm):
  """
  Returns the function wrapped by the #staticmethod *cm*.
  """

  if hasattr(cm, '__func__'):
    return cm.__func__
  else:
    return cm.__get__(int)


def mro_resolve(name, bases, dict):
  """
  Given a tuple of baseclasses and a dictionary that takes precedence
  over any value in the bases, finds a value with the specified *name*
  and returns it. Raises #KeyError if the value can not be found.
  """

  if name in dict:
    return dict[name]
  for base in bases:
    if hasattr(base, name):
      return getattr(base, name)
    try:
      return mro_resolve(name, base.__bases__, {})
    except KeyError:
      pass
  raise KeyError(name)


class InlineMetaclass(type):
  """
  This is the metaclass for the #InlineMetaclassConstructor base class. It will
  call the special methods `__metanew__()` and `__metainit__()` of the
  constructed class. This avoids creating a new metaclass and allows to put the
  meta-constructor code in the same class.

  Note that the implementation does not take multiple inheritance into
  account and will simply call the first method found in the MRO.

  ```python
  class MyClass(metaclass=InlineMetaclass):
    def __metanew__(meta, name, bases, dict):
      # Do the stuff you would usually do in your metaclass.__new__()
      return super(InlineMetaclass, meta).__new__(meta, name, bases, dict)
    def __metainit__(cls, name, bases, dict):
      # Do the stuff you would usually do in your metaclass.__init__()
      pass
  ```
  """

  def __new__(cls, name, bases, dict):
    # Make sure the __metanew__() and __metainit__() functions
    # are classmethods.
    if '__metanew__' in dict:
      dict['__metanew__'] = staticmethod(dict['__metanew__'])
    if '__metainit__' in dict:
      dict['__metainit__'] = classmethod(dict['__metainit__'])

    # TODO: Py3k: Add the `__class__` cell to the metanew and metainit
    #       methods so that super() can be used.

    # Call the __metanew__() method if available.
    try:
      metanew = mro_resolve('__metanew__', bases, dict)
    except KeyError:
      return super(InlineMetaclass, cls).__new__(cls, name, bases, dict)
    else:
      if isinstance(metanew, staticmethod):
        metanew = get_staticmethod_func(metanew)
      return metanew(cls, name, bases, dict)

  def __init__(self, name, bases, dict):
    try:
      metainit = getattr(self, '__metainit__')
    except AttributeError:
      pass
    else:
      return metainit(name, bases, dict)


# This is an instance of the :class:`InlineMetaclass` that can
# be subclasses to inherit the metaclass functionality. We do
# this for Python 2/3 compatibility.
InlineMetaclassBase = InlineMetaclass('InlineMetaclassBase', (), {})


def copy_class(cls, new_bases=None, new_name=None, update_attrs=None,
               resolve_metaclass_conflict=False):
  """ Creates a copy of the class *cls*, optionally with new bases and a
  new class name. Additional attributes may be added with the *update_attrs*
  argument, which may be a dictionary or a callable that accepts the original
  attributes and returns the new attributes.

  If the *new_bases* would result in a metaclass conflict, and
  *resolve_metaclass_conflict* is set to True, [[get_noconflict_metaclass()]]
  is used to construct a new metaclass that resolves the conflict.

  Alternatively, *resolve_metaclass_conflict* may also be a callable with
  the same interface as [[get_noconflict_metaclass()]]. """

  attrs = vars(cls).copy()
  attrs.pop('__weakref__', None)
  attrs.pop('__dict__', None)

  if callable(update_attrs):
    attrs = update_attrs(attrs)
  elif update_attrs:
    attrs.update(update_attrs)

  if resolve_metaclass_conflict is True:
    resolve_metaclass_conflict = globals()['resolve_metaclass_conflict']

  if new_bases is None:
    new_bases = cls.__bases__
    metaclass = type(cls)
  elif resolve_metaclass_conflict and get_conflicting_metaclasses((), new_bases):
    metaclass = resolve_metaclass_conflict((), new_bases)
  else:
    metaclass = type(cls)

  return metaclass(new_name or cls.__name__, new_bases, attrs)


def get_conflicting_metaclasses(metaclasses=(), bases=()):
  """ Checks if any of classes in *metaclasses* are conflicting (or any of
  the metaclasses of *bases*). Returns a list of conflicting metaclasses. """

  metaclasses = tuple(unique(chain(metaclasses, map(type, bases))))
  conflicts = []
  for x in metaclasses:
    for y in metaclasses:
      if x is y: continue
      if not (issubclass(x, y) or issubclass(y, x)):
        if x not in conflicts:
          conflicts.append(x)
        if y not in conflicts:
          conflicts.append(y)
  return conflicts


def resolve_metaclass_conflict(metaclasses=(), bases=(), _cache={}):
  """ Resolves a metaclass conflict for the specified *bases*. Note that this
  will not check if there is a conflict and simply produce a new metaclass
  that combines the metaclasses of *metaclasses* or *bases*. """

  metaclasses = tuple(unique(chain(metaclasses, map(type, bases))))
  if metaclasses in _cache:
    return _cache[metaclasses]

  name = '_' + '_'.join(x.__name__ for x in metaclasses)
  result = type(name, metaclasses, {})
  _cache[metaclasses] = result
  return result
