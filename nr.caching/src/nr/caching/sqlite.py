
import math
import sqlite3
import string
import time
import typing as t
from contextlib import closing

from .api import KeyValueStore, KeyDoesNotExist, NamespaceDoesNotExist


def _fetch_all(cursor: sqlite3.Cursor) -> t.Iterable[t.Tuple]:
  while True:
    rows = cursor.fetchmany()
    if not rows:
      break
    yield from rows


class SqliteStore(KeyValueStore):
  """
  Implements a key-value store on top of an Sqlite3 database. Namespaces are represented as
  tables in the database. Value expiration only has a second-resolution (rounded up). Namespaces
  can only consist of ASCII letters, digits, underscores, dots and hyphens.
  """

  NAMESPACE_CHARS = frozenset(string.ascii_letters + string.digits + '._-')

  def __init__(self, filename: str) -> None:
    self._conn = sqlite3.connect(filename)
    self._created_namespaces: t.Set[str] = set()

  @staticmethod
  def _get_time(add: int) -> int:
    return int(math.ceil(time.time() + add))

  @staticmethod
  def _validate_namespace(namespace: str) -> None:
    if set(namespace) - SqliteStore.NAMESPACE_CHARS:
      raise ValueError(f'invalid namespace name: {namespace!r}')

  @staticmethod
  def _get_namespaces(cursor: sqlite3.Cursor) -> t.Iterable[str]:
    cursor.execute('''SELECT name FROM sqlite_master
      WHERE type = 'table' AND name NOT like 'sqlite_%';''')
    yield from (x[0] for x in _fetch_all(cursor))

  def get_namespaces(self) -> t.Iterator[str]:
    """
    Returns an iterator that returns the name of all namespaces known to the Sqlite store. Note
    that new namespaces are created on-deman using #store().
    """

    with closing(self._conn.cursor()) as cursor:
      yield from self._get_namespaces(cursor)

  def get_keys(self, namespace: str) -> t.Iterator[t.Tuple[str, t.Optional[int]]]:
    """
    Returns an iterator that returns all keys in the specified *namespace* and their expiration
    timestamp. This includes any keys that are already expired but not yet expunged.
    """

    with closing(self._conn.cursor()) as cursor:
      try:
        cursor.execute('SELECT key, exp FROM "' + namespace + '"')
      except sqlite3.OperationalError as exc:
        if 'no such table' in str(exc):
          raise NamespaceDoesNotExist(namespace)
        raise
      yield from t.cast(t.Iterator[t.Tuple[str, t.Optional[int]]], _fetch_all(cursor))

  def _ensure_namespace(self, cursor: sqlite3.Cursor, namespace: str) -> None:
    self._validate_namespace(namespace)
    if namespace not in self._created_namespaces:
      cursor.execute('''
        CREATE TABLE IF NOT EXISTS "''' + namespace + '''"
        (key TEXT PRIMARY KEY, value BLOB, exp INTEGER)''')
      self._created_namespaces.add(namespace)

  # KeyValueStore

  def load(self, namespace: str, key: str) -> t.Optional[bytes]:
    self._validate_namespace(namespace)
    with closing(self._conn.cursor()) as cursor:
      try:
        cursor.execute('''
          SELECT value FROM "''' + namespace + '''"
            WHERE key = ? AND (? < exp OR exp IS NULL)''',
          (key, self._get_time(0)),
        )
      except sqlite3.OperationalError as exc:
        if 'no such table' in str(exc):
          raise NamespaceDoesNotExist(namespace)
        raise
      result = cursor.fetchone()
      if result is None:
        raise KeyDoesNotExist(namespace, key)
      return result[0]

  def store(self, namespace: str, key: str, value: bytes, expires_in: t.Optional[int]) -> None:
    self._validate_namespace(namespace)
    with closing(self._conn.cursor()) as cursor:

      # Create the table for the namespace if it does not exist.
      self._ensure_namespace(cursor, namespace)

      # Insert the value into the database.
      exp = self._get_time(expires_in) if expires_in is not None else None
      cursor.execute('''
        INSERT OR REPLACE INTO ''' + namespace  + '''
        VALUES (?, ?, ?)''',
        (key, value, exp),
      )

      self._conn.commit()

  def expunge(self) -> None:
    with closing(self._conn.cursor()) as cursor:
      for namespace in list(self._get_namespaces(cursor)):
        cursor.execute('''
          DELETE FROM "''' + namespace + '''" WHERE exp < ?''',
          (self._get_time(0),),
        )
      self._conn.commit()

  # NamespaceAware

  def ensure_namespace(self, namespace: str) -> None:
    with closing(self._conn.cursor()) as cursor:
      self._ensure_namespace(cursor, namespace)
      self._conn.commit()

  def drop_namespace(self, namespace: str) -> None:
    self._validate_namespace(namespace)
    with closing(self._conn.cursor()) as cursor:
      try:
        cursor.execute('DROP TABLE "' + namespace + '"')
      except sqlite3.OperationalError as exc:
        if 'no such table' in str(exc):
          raise NamespaceDoesNotExist(namespace)
        raise
      self._conn.commit()
