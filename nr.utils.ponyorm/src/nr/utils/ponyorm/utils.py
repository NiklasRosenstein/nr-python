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

from .appdb import AppEntityMeta
import enum
import pony.orm
from typing import Tuple

__all__ = ['get_db', 'get_one', 'get_or_create', 'upsert']


def get_db(entity):
  """
  Returns the #pony.orm.Database backing the #Entity instance *entity*.
  """

  return entity._database_


def get_one(entity_cls, kwargs):
  """
  Same as `entity_cls.get()` except that you can pass an argument with
  the name "entity".
  """

  try:
    return entity_cls._find_one_(kwargs)
  except pony.orm.ObjectNotFound:
    return None


def get_or_create(entity_cls, get, set=None):
  # type: (Type[Entity], dict, Optional[dict]) -> Tuple[Entity, Bool]
  """
  Alias for `upsert(entity_cls, get, set, mutate=False)`.
  """

  return upsert(entity_cls, get, set, mutate=False)


def upsert(entity_cls, get, set=None, mutate=True):
  # type: (Type[Entity], dict, Optional[dict]) -> Tuple[Entity, Bool]
  """
  Update or create an object of the Pony ORM *entity_cls*. The *get*
  dictionary identifies the object, the *set* dictionary specifies the
  values to set/pass to the constructor.

  If *mutate* is set to #True (the default) and an object with the *get*
  values has already been found, it will be updated. Otherwise, a new
  object will be created.

  Returns the retrieved or newly created object and a boolean that indicates
  whether it was just created or retrieved from the database.
  """

  assert isinstance(entity_cls, (pony.orm.core.EntityMeta, AppEntityMeta)), \
    "{!r} is not an Entity class".format(entity_cls)

  set = set or {}
  obj = get_one(entity_cls, get)
  if obj is None:
    obj = entity_cls(**get, **set)
    created = True
  elif mutate:
    created = False
    for key, value in set.items():
      setattr(obj, key, value)
  else:
    created = False

  return obj, created
