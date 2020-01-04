
import enum
import pony.orm

from typing import Tuple


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
  """
  Alias for `upsert(entity_cls, get, set, mutate=False)`.
  """

  return upsert(entity_cls, get, set, mutate=False)


def upsert(entity_cls, get, set=None, mutate=True):  # type: (...) -> Tuple['entity_cls', bool]
  """
  Update or create an object of the Pony ORM *entity_cls*. The *get*
  dictionary identifies the object, the *set* dictionary specifies the
  values to set/pass to the constructor.
  """

  assert isinstance(entity_cls, pony.orm.core.EntityMeta), \
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
