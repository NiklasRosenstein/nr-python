
import dataclasses
import typing as t


@dataclasses.dataclass
class AWSGIConfig:
  host: t.Optional[str] = None
  port: t.Optional[int] = 8000
  unix_socket: t.Optional[str] = None
  workers: t.Optional[int] = None
