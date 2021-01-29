
import json
import hashlib
import sys
import typing as t
from dataclasses import dataclass

from overrides import overrides  # type: ignore

from .api import KeyValueStore, KeyDoesNotExist, NamespaceStore, NamespaceDoesNotExist

JsonObject = t.Dict[str, t.Any]
T = t.TypeVar('T')
_NotSet = object()


def hash_args(*args: t.Any) -> str:
  """
  Accepts a list of arbitrary values that are expected to be JSON serializable and generates an
  MD5 hash of the data. This is useful to parametrize a key.
  """

  return hashlib.md5(json.dumps(args).encode('utf-8')).hexdigest()


@dataclass
class _JsonCacheBase:
  default_exp: t.Optional[int] = None
  encoding: str = 'utf-8'
  encoder: t.Type[json.JSONEncoder] = json.JSONEncoder
  decoder: t.Type[json.JSONDecoder] = json.JSONDecoder


class JsonCacheFactory(_JsonCacheBase):
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
    store: NamespaceStore,
    default_exp: t.Optional[int] = None,
    encoding: str = 'utf-8',
    encoder: t.Type[json.JSONEncoder] = json.JSONEncoder,
    decoder: t.Type[json.JSONDecoder] = json.JSONDecoder,
  ) -> None:

    super().__init__(default_exp, encoding, encoder, decoder)
    self._store = store

  def namespace(self, namespace: str) -> 'JsonCache':
    return JsonCache(
      self._store.namespace(namespace),
      self.default_exp,
      self.encoding,
      self.encoder,
      self.decoder)


class JsonCache(_JsonCacheBase):

  def __init__(self,
    store: KeyValueStore,
    default_exp: t.Optional[int] = None,
    encoding: str = 'utf-8',
    encoder: t.Type[json.JSONEncoder] = json.JSONEncoder,
    decoder: t.Type[json.JSONDecoder] = json.JSONDecoder,
  ) -> None:

    super().__init__(default_exp, encoding, encoder, decoder)
    self._store = store

  def load(self, key: str) -> JsonObject:
    data = self._store.load(key)
    assert data is not None, "NULL value is unexpected"
    return json.loads(data.decode(self.encoding), cls=self.decoder)

  @t.overload
  def store(self, key: str, value: JsonObject) -> None:
    pass  # Overload def

  @t.overload
  def store(self, key: str, value: JsonObject, expires_in: t.Optional[int] = None) -> None:
    pass  # Overload def

  def store(self, key, value, expires_in = _NotSet) -> None:
    """
    Store a value into the specified namespace/key. If *expires_in* is not specified, the
    default expiration time will be used. Passing #None into *expires_in* will use store the
    value without expiration, even if a default expiration is set.
    """

    if expires_in is _NotSet:
      expires_in = self.default_exp

    assert isinstance(expires_in, int) or expires_in is None, type(expires_in)
    data = json.dumps(value, cls=self.encoder).encode(self.encoding)
    self._store.store(key, data, expires_in)

  def load_or_none(self, key: str) -> t.Optional[JsonObject]:
    """
    Loads a JSON value from the underlying key-value store as identified by the specified *key*,
    but unlike #load() this method will return #None instead of raising a #KeyDoesNotExist error
    if the key does not exist.
    """

    try:
      return self.load(key)
    except KeyDoesNotExist:
      return None

  def loading(self,
    key: str,
    or_get: t.Callable[[], JsonObject],
    if_: bool = True,
    expires_in: t.Optional[int] = None,
  ) -> JsonObject:
    """
    Loads a value from the specified key, or falls back to calling the *or_get* function and
    storing it's result. When *if_* is set to #False, *or_get* will always be called regardless
    of whether the key exists in the store or not.
    """

    try:
      if if_:
        return self.load(t.cast(str, key))
    except KeyDoesNotExist:
      pass  # fallback

    value = or_get()
    self.store(key, value, expires_in)
    return value

  def evolve(self,
    key: str,
    update: t.Callable[[JsonObject], T],
    if_: bool = True,
    save_on_error: bool = True,
    expires_in: t.Optional[int] = None,
  ) -> T:
    """
    Retrieves a JSON object stored under the specified key and passes it into the *update*
    function. If the key does not exist, an empty dictionary will be used. After *update* was
    called, the same dictionary will be stored again under the same key. The return value of the
    *update* function is returned from this function.

    With *save_on_error* enabled (default), the dictionary passed into *update* will be stored
    even if an exception occurred in the *update* function.

    The expiration time of the key will be renewed when calling this function.
    """

    value = (self.load_or_none(key) or {}) if if_ else {}
    try:
      return update(value)
    finally:
      if not sys.exc_info() or save_on_error:
        self.store(key, value, expires_in)
