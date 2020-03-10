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
This module is a layer on top of the #pony.orm package that allows you to
declare entities in module level and bind them to a database at a later
stage.
"""

from nr.pylang.utils.funcdef import copy_function
from pony.orm import Database
from pony.orm.core import Attribute, Index
import pony.orm
import types
import weakref


def _mock_attribute_subclass(cls):
  class mocked_cls(cls):
    def __init__(self, *args, **kwargs):
      self._init_args = (args, kwargs)
      super().__init__(*args, **kwargs)
    def clone(self):
      return mocked_cls(*self._init_args[0], **self._init_args[1])
  mocked_cls.__name__ = cls.__name__
  mocked_cls.__qualname__ = mocked_cls.__qualname__.rpartition('.')[0] + '.' + cls.__name__
  return mocked_cls


Optional = _mock_attribute_subclass(pony.orm.Optional)
Required = _mock_attribute_subclass(pony.orm.Required)
PrimaryKey = _mock_attribute_subclass(pony.orm.PrimaryKey)
Set = _mock_attribute_subclass(pony.orm.Set)
Discriminator = _mock_attribute_subclass(pony.orm.Discriminator)


class _EntityCloneHelper(object):

  def __init__(self):
    self._conversion_map = {}

  def clone_attr(self, obj):
    assert isinstance(obj, Attribute)
    assert hasattr(obj, 'clone')
    new = self._conversion_map.get(obj)
    if new is None:
      new = self._conversion_map[obj] = obj.clone()
    return new

  def clone_index(self, obj):
    assert isinstance(obj, Index)
    new = self._conversion_map.get(obj)
    if new is None:
      new = copy.copy(obj)
      new.attrs = [self.clone(x) for x in obj.attrs]
      self._conversion_map[obj] = new
    return new


class AppEntityMeta(type):

  _app_database = None
  _bound_entity = None

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    if self._app_database is not None:
      self._app_database()._register_entity_class(self)

  def __repr__(self):
    name = self.__name__
    if self._app_database is not None:
      name = self._app_database().app_namespace + '.' + name
    return '<Entity {!r}>'.format(name)

  def __iter__(self):
    return iter(self.bound_entity)

  def __getattr__(self, name):
    if self._bound_entity is None:
      raise AttributeError(name)
    return getattr(self._bound_entity(), name)

  def __getitem__(self, pk):
    if self._bound_entity is None:
      raise RuntimeError('{} is not bound yet'.format(self.__name__))
    return self._bound_entity()[pk]

  def clone(self, new_base):
    members = dict(vars(self))
    helper = _EntityCloneHelper()
    for key, value in members.items():
      if isinstance(value, Attribute):
        members[key] = helper.clone_attr(value)
      elif isinstance(value, Index):
        members[key] = helper.clone_index(value)
    return type(self)(self.__name__, (new_base,), members)

  @property
  def bound_entity(self):
    return None if self._bound_entity is None else self._bound_entity()


class AppEntity(metaclass=AppEntityMeta):

  def __new__(cls, *args, **kwargs):
    bound_entity = cls.bound_entity
    if not bound_entity:
      raise RuntimeError('{} is not bound'.format(cls))
    return bound_entity(*args, **kwargs)

  def get_init_attr(self, kwargs, name):
    """
    Returns the value of *name* in *kwargs* or the default value for the
    column *name* if it is not existing in *kwargs*. The *kwargs* will
    be updated with that default value.
    """

    if name in kwargs:
      return kwargs[name]
    attr = getattr(self, name)
    if attr.default is not None:
      if callable(attr.default):
        kwargs[name] = attr.default()
      else:
        kwargs[name] = attr.default
    return kwargs[name]


class AppDatabase:
  """
  A mock for a Pony ORM database object that allows you to derive from
  an #Entity class to create late-binding database models. When the real
  Pony ORM database is created, the app models are registered with a
  prefix to prevent name collisions.
  """

  def __init__(self, app_namespace: str):
    self.app_namespace = app_namespace
    self.entities = {}
    self.Entity = AppEntityMeta(app_namespace + '.Entity', (AppEntity,), {})
    self.Entity._app_database = weakref.ref(self)
    self.bound_db = None
    self.bound_entities = None
    self.converter_classes = []

  def __getattr__(self, name):
    if self.bound_db is None:
      raise AttributeError(name)
    if name in self.bound_entities:
      return self.bound_entities[name]
    return getattr(self.bound_db, name)

  def _register_entity_class(self, cls):
    self.entities[cls.__name__] = cls

  def clone(self):
    """
    Clones this #AppDatabase and all its declared entitie. Note that this
    will create copies of all declared entities and this #AppDatabase
    instance. The returned database will be unbound.

    > _Important_: Cloning second-level entity subclasses is currently
    > not supported.
    """

    db = type(self)(self.app_namespace)
    for name, entity in self.entities.items():
      if entity.__bases__ != (self.Entity,):
        msg = "Cloning second-level or multiple-inheritance entities is "\
              "currently not supported (entity {!r} has bases [{}])."
        bases = ', '.join(x.__name__ for x in entity.__bases__)
        raise RuntimeError(msg.format(entity.__name__, bases))
      entity.clone(db.Entity)
      assert name in db.entities
    return db

  def bind_to(self, db: 'Database'):
    """
    Binds the entities declared in the #AppDatabase to an actual Pony ORM
    database object. The #bound_entities attribute will be set to a
    dictionary that contains all entities bound to the database.
    """

    assert isinstance(db, Database)

    if None not in (self.bound_db, self.bound_entities):
      raise RuntimeError('AppDatabase {!r} is already bound'
        .format(self.app_namespace))

    self.bound_db = db
    self.bound_entities = {}
    for name, entity_decl in self.entities.items():
      members = vars(entity_decl).copy()
      members.setdefault('_table_', name)
      members['_table_'] = self.app_namespace + '.' + members['_table_']
      db_entity = type(name, (db.Entity,), members)
      for key, value in vars(db_entity).items():
        if isinstance(value, types.FunctionType):
          value = copy_function(value, closure={'__class__': db_entity})
          setattr(db_entity, key, value)
      entity_decl._bound_entity = weakref.ref(db_entity)
      self.bound_entities[name] = db_entity

    # TODO (@NiklasRosenstein): Is there a way we can limit the use of a
    #   converted to just the entities that are defined in this app db?
    db.provider.converter_classes.extend(self.converter_classes)

  def is_bound(self):
    return self.bound_db is not None

  def drop_all_tables(self, with_all_data=False):
    for entity in self.bound_entities.values():
      self.bound_db.drop_table(entity, True, with_all_data)

  def drop_table(self, table_name, if_exists=False, with_all_data=False):
    table = self.bound_entities[table_name] if isinstance(table_name, str) \
            else table_name
    if table not in self.bound_entities.values():
      raise ValueError('{!r} is not an entity of app database {!r}'.format(
        table.__name__, self.app_namespace))
    self.bound_db.drop_table(table_name, if_exists, with_all_data)

  def register_converter(self, cls, converter_cls=None):
    if converter_cls is None:
      converter_cls, cls = cls, None
    if cls is None:
      if not hasattr(converter_cls, 'for_types'):
        raise TypeError('converter_cls requires a for_types attribute if '
                        'cls is not specified.')
      for type_ in converter_cls.for_types:
        assert type_ is not None  # prevent infinite recursion
        self.register_converter(type_, converter_cls)
    else:
      if self.bound_db:
        self.bound_db.provider.converter_classes.append((cls, converter_cls))
      self.converter_classes.append((cls, converter_cls))


__all__ = [
  'Optional',
  'Required',
  'PrimaryKey',
  'Set',
  'Discriminator',
  'AppEntity',
  'AppDatabase'
]
