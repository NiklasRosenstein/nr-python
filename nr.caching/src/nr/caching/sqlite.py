
import contextlib
import math
import sqlite3
import string
import threading
import time
import typing as t
from contextlib import closing

from overrides import overrides  # type: ignore

from .api import KeyValueStore, KeyDoesNotExist, NamespaceStore, NamespaceDoesNotExist


def _fetch_all(cursor: sqlite3.Cursor) -> t.Iterable[t.Tuple]:
  while True:
    rows = cursor.fetchmany()
    if not rows:
      break
    yield from rows


class SqliteStore(NamespaceStore):
  """
  Implements a key-value store on top of an Sqlite3 database. Namespaces are represented as
  tables in the database. Value expiration only has a second-resolution (rounded up). Namespaces
  can only consist of ASCII letters, digits, underscores, dots and hyphens.

  The SqliteStore is thread-safe, but may be slow to access concurrently due to locking
  requirements.
  """

  NAMESPACE_CHARS = frozenset(string.ascii_letters + string.digits + '._-')

  def __init__(self, filename: str) -> None:
    self._lock = threading.Lock()
    self._conn = sqlite3.connect(filename, check_same_thread=False)
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

  @contextlib.contextmanager
  def _locked_cursor(self) -> t.Iterator[sqlite3.Cursor]:
    with self._lock, closing(self._conn.cursor()) as cursor:
      yield cursor

  def get_namespaces(self) -> t.Iterator[str]:
    """
    Returns an iterator that returns the name of all namespaces known to the Sqlite store. Note
    that new namespaces are created on-deman using #store().
    """

    with self._locked_cursor() as cursor:
      yield from self._get_namespaces(cursor)

  def get_keys(self, namespace: str) -> t.Iterator[t.Tuple[str, t.Optional[int]]]:
    """
    Returns an iterator that returns all keys in the specified *namespace* and their expiration
    timestamp. This includes any keys that are already expired but not yet expunged.
    """

    with self._locked_cursor() as cursor:
      try:
        cursor.execute(f'SELECT key, exp FROM "{namespace}"')
      except sqlite3.OperationalError as exc:
        if 'no such table' in str(exc):
          raise NamespaceDoesNotExist(namespace)
        raise
      yield from t.cast(t.Iterator[t.Tuple[str, t.Optional[int]]], _fetch_all(cursor))

  def _ensure_namespace(self, cursor: sqlite3.Cursor, namespace: str) -> None:
    self._validate_namespace(namespace)
    if namespace not in self._created_namespaces:
      cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS "{namespace}"
        (key TEXT PRIMARY KEY, value BLOB, exp INTEGER)''')
      self._created_namespaces.add(namespace)

  def load(self, namespace: str, key: str) -> bytes:
    self._validate_namespace(namespace)
    with self._locked_cursor() as cursor:
      try:
        cursor.execute(f'''
          SELECT value FROM "{namespace}"
            WHERE key = ? AND (? < exp OR exp IS NULL)''',
          (key, self._get_time(0)),
        )
      except sqlite3.OperationalError as exc:
        if 'no such table' in str(exc):
          raise NamespaceDoesNotExist(namespace)
        raise
      result = cursor.fetchone()
      if result is None:
        raise KeyDoesNotExist(namespace + ':' + key)
      if not isinstance(result[0], bytes):
        raise RuntimeError(f'expected data to be bytes, got {type(result[0]).__name__}')
      return result[0]

  def store(self, namespace: str, key: str, value: bytes, expires_in: t.Optional[int]) -> None:
    self._validate_namespace(namespace)
    with self._locked_cursor() as cursor:

      # Create the table for the namespace if it does not exist.
      self._ensure_namespace(cursor, namespace)

      # Insert the value into the database.
      exp = self._get_time(expires_in) if expires_in is not None else None
      cursor.execute(f'''
        INSERT OR REPLACE INTO "{namespace}"
        VALUES (?, ?, ?)''',
        (key, value, exp),
      )

      self._conn.commit()

  @overrides
  def namespace(self, namespace: str) -> KeyValueStore:
    with self._locked_cursor() as cursor:
      self._ensure_namespace(cursor, namespace)
    return SqliteKeyValueStore(self, namespace)

  @overrides
  def expunge(self, namespace: t.Optional[str] = None) -> None:
    with self._locked_cursor() as cursor:
      for namespace in [namespace] if namespace else list(self._get_namespaces(cursor)):
        cursor.execute(f'''
          DELETE FROM "{namespace}" WHERE exp < ?''',
          (self._get_time(0),),
        )
      self._conn.commit()


class SqliteKeyValueStore(KeyValueStore):

  def __init__(self, store: SqliteStore, namespace: str) -> None:
    self._store = store
    self._namespace = namespace

  @overrides
  def load(self, key: str) -> bytes:
    return self._store.load(self._namespace, key)

  @overrides
  def store(self, key: str, value: bytes, expires_in: t.Optional[int] = None) -> None:
    self._store.store(self._namespace, key, value, expires_in)

  @overrides
  def expunge(self) -> None:
    self._store.expunge(self._namespace)
