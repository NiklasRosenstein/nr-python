
import dataclasses
import typing as t

from .logging import LoggerConfig

T_ApplicationConfig = t.TypeVar('T_ApplicationConfig', bound='ApplicationConfig')


@dataclasses.dataclass
class ApplicationConfig:
  """
  Base class for application configurations.
  """

  logging: LoggerConfig = dataclasses.field(default_factory=LoggerConfig)
