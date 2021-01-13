
import json
import hashlib
import sys
import typing as t

from .api import KeyValueStore, KeyDoesNotExist, NamespaceAware, NamespaceDoesNotExist

JsonObject = t.Dict[str, t.Any]
T = t.TypeVar('T')


class JsonCache(NamespaceAware):
  """
  A caching layer on top of a #KeyValueStore that serializes/deserializes values to and from
  JSON. It provides a few useful methods to streamline cache integration in code with as little
  intrusion into the readability as possible.

  Values stored in this cache can only be JSON objects.

  # Arguments

  implict_namespaces (bool): Enabled by default. If enabled, #load_or_none() and #loading() will
    interpret #NamespaceDoesNotExist the same as a #KeyDoesNotExist.
  """

  def __init__(self,
    store: KeyValueStore,
    default_exp: t.Optional[int] = None,
    encoding: str = 'utf-8',
    encoder: t.Type[json.JSONEncoder] = json.JSONEncoder,
    decoder: t.Type[json.JSONDecoder] = json.JSONDecoder,
    implict_namespaces: bool = True,
  ) -> None:

    self._store = store
    self._default_exp = default_exp
    self._encoding = encoding
    self._encoder = encoder
    self._decoder = decoder
    self._implict_namespaces = implict_namespaces

  def load(self, namespace: str, key: str) -> JsonObject:
    """
    Loads a value from the given namespace/key.
    """

    data = self._store.load(namespace, key)
    assert data is not None, "NULL value is unexpected"
    return json.loads(data.decode(self._encoding), cls=self._decoder)

  def load_or_none(self, namespace: str, key: str) -> t.Optional[JsonObject]:
    """
    Loads a value from the given namespace/key, returning #None if the key or namespace does not
    exist. If *implict_namespaces* is enabled, a #NamespaceDoesNotExist error is also caught and
    interpreted the same as #KeyDoesNotExist.
    """

    try:
      return self.load(namespace, key)
    except KeyDoesNotExist:
      return None
    except NamespaceDoesNotExist:
      if self._implict_namespaces:
        return None
      raise

  def store(self,
    namespace: str,
    key: str,
    value: JsonObject,
    expires_in: t.Optional[int] = None,
  ) -> None:
    """
    Store a value into the specified namespace/key. If *expires_in* is not specified, the
    default expiration time will be used.
    """

    if expires_in is None:
      expires_in = self._default_exp

    data = json.dumps(value, cls=self._encoder).encode(self._encoding)
    self._store.store(namespace, key, data, expires_in)

  def loading(self,
    namespace: str,
    key: t.Union[str, t.Any],
    or_get: t.Callable[[], JsonObject],
    if_: bool = True,
    expires_in: t.Optional[int] = None,
  ) -> JsonObject:
    """
    Loads a value from the specified namespace/key. If the key does not exist, *or_get* is called
    to retrieve the value instead. The value returned by *or_get* will be stored. The *if_*
    parameter can be set to *False* to always call *or_get*.

    If *key* is not a string, it must be a tuple of JSON serializable objects. The entire tuple
    will be serialized and subsequently hashed using MD5, which represents the new key.
    """

    if not isinstance(key, str):
      key = hashlib.md5(json.dumps(key).encode(self._encoding)).hexdigest()

    try:
      if not if_:
        raise KeyDoesNotExist(namespace, key)
      return self.load(namespace, t.cast(str, key))
    except (KeyDoesNotExist, NamespaceDoesNotExist) as e:
      if not self._implict_namespaces and isinstance(e, NamespaceDoesNotExist):
        raise
      value = or_get()
      self.store(namespace, t.cast(str, key), value, expires_in)
      return value

  def evolve(self,
    namespace: str,
    key: t.Union[str, t.Any],
    update: t.Callable[[JsonObject], T],
    if_: bool = True,
    save_on_error: bool = True,
    expires_in: t.Optional[int] = None,
  ) -> T:
    """
    Retrieves a JSON object stored under the specified namespace/key and passes it into *update*.
    If the key does not exist, an empty dictionary will be used. After *update* was called, the
    same dictionary will be stored again under the same namespace/key. The return value of the
    *update* function is returned from this function.

    With *save_on_error* enabled (default), the dictionary passed into *update* will be stored
    even if an exception occurrs in the *update* function.

    The expiration time of the key will be renewed when calling this function.
    """

    if not isinstance(key, str):
      key = hashlib.md5(json.dumps(key).encode(self._encoding)).hexdigest()

    value = (self.load_or_none(namespace, key) or {}) if if_ else {}
    try:
      return update(value)
    finally:
      if not sys.exc_info() or save_on_error:
        self.store(namespace, key, value, expires_in)

  # NamespaceAware

  def ensure_namespace(self, namespace: str) -> None:
    self._store.ensure_namespace(namespace)

  def drop_namespace(self, namespace: str) -> None:
    self._store.drop_namespace(namespace)
