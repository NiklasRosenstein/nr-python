
import abc
import dataclasses
import typing as t


@dataclasses.dataclass
class NamespaceDoesNotExist(Exception):
  namespace: str


@dataclasses.dataclass
class KeyDoesNotExist(Exception):
  key: str


class KeyValueStore(metaclass=abc.ABCMeta):
  """
  Interface for a simplistic key-value store based on unicode strings and binary values. On
  storing, values can be associated with an expiration time. The storage for expired values may
  be immediately reclaimed using the #expunge() method, but may also be automatically reclaimed
  over time.
  """

  @abc.abstractmethod
  def load(self, key: str) -> bytes:
    """
    Load the value for a given key. Raises a #KeyDoesNotExist exception if the key can not be
    found in the store (for example because it never existed or because it expired).
    """

    pass

  @abc.abstractmethod
  def store(self, key: str, value: bytes, expires_in: t.Optional[int] = None) -> None:
    """
    Store a value for the given key. If specified, *expires_in* must be an integer describing the
    seconds after which the value is set to expire in the store. If no expiration time is
    specified, the value will be stored indefinitely. Setting *expires_in* to 0 is equivalent to
    deleting the key.
    """

    pass

  @abc.abstractmethod
  def expunge(self) -> None:
    """
    Explicitly expunge any expired values from the store.
    """

    pass


class NamespaceStore(metaclass=abc.ABCMeta):
  """
  Interface that provides key-value stores based on a namespace identifier.
  """

  @abc.abstractmethod
  def namespace(self, namespace: str) -> KeyValueStore:
    pass

  @abc.abstractmethod
  def expunge(self, namespace: t.Optional[str] = None) -> None:
    pass
