
import dataclasses
import typing as t

from ..application.config import ApplicationConfig

T_AWSGIApplicationConfig = t.TypeVar('T_AWSGIApplicationConfig', bound='AWSGIApplicationConfig')


@dataclasses.dataclass
class ServerConfig:
  host: t.Optional[str] = None
  port: t.Optional[int] = 8000
  unix_socket: t.Optional[str] = None
  workers: t.Optional[int] = None


@dataclasses.dataclass
class AWSGIApplicationConfig(ApplicationConfig):
  server: ServerConfig = dataclasses.field(default_factory=ServerConfig)
