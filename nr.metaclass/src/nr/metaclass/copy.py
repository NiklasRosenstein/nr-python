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

from .deconflict import get_conflicting_metaclasses, \
  resolve_metaclass_conflict as _resolve_metaclass_conflict, \
  reduce_mro as _reduce_mro


def copy_class(cls, new_bases=None, new_name=None, new_qualname=None,
               module=None, update_attrs=None, resolve_metaclass_conflict=False,
               reduce_mro=False):
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

  if new_name:
    attrs['__name__'] = new_name
  if new_qualname:
    attrs['__qualname__'] = new_qualname
  if module:
    attrs['__module__'] = module

  if resolve_metaclass_conflict is True:
    resolve_metaclass_conflict = _resolve_metaclass_conflict
  if reduce_mro is True:
    reduce_mro = _reduce_mro

  if reduce_mro:
    new_bases = reduce_mro(*new_bases)

  if new_bases is None:
    new_bases = cls.__bases__
    metaclass = type(cls)
  elif resolve_metaclass_conflict and get_conflicting_metaclasses((), new_bases):
    metaclass = resolve_metaclass_conflict((), new_bases)
  else:
    metaclass = type(cls)

  return metaclass(new_name or cls.__name__, new_bases, attrs)
