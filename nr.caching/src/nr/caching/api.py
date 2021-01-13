
import abc
import dataclasses
import typing as t


@dataclasses.dataclass
class NamespaceDoesNotExist(Exception):
  namespace: str


@dataclasses.dataclass
class KeyDoesNotExist(Exception):
  namespace: str
  key: str


class NamespaceAware(metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def ensure_namespace(self, namespace: str) -> None:
    """
    Ensure that the specified namespace exists.
    """

    pass

  @abc.abstractmethod
  def drop_namespace(self, namespace: str) -> None:
    """
    Drop an entire namespace.
    """

    pass


class KeyValueStore(NamespaceAware, metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def load(self, namespace: str, key: str) -> t.Optional[bytes]:
    """
    Load the value for a given namespace/key pair. Raises a #NamespaceError if the namespace
    does not exist. Raises a #KeyError if the key does not exist in the namespace. Expired
    values are treated as non-existent.
    """

    pass

  @abc.abstractmethod
  def store(self, namespace: str, key: str, value: bytes, expires_in: t.Optional[int]) -> None:
    """
    Store a value for the given namespace/key pair. If specified, *expires_in* must be an
    integer describing the seconds after which the value is set to expire in the store. If no
    expiration time is specified, the value will be stored indefinitely. Setting *expires_in*
    to 0 is equivalent to deleting the key.

    Implementations may decide for themselves whether they automatically create the namespace
    if it does not exist yet. If they decide not to, clients must call #ensure_namespace()
    beforehand.
    """

    pass

  @abc.abstractmethod
  def expunge(self) -> None:
    """
    Expunge any expired values from the key-value store.
    """

    pass
