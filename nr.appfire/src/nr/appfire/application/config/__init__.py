
from .logging import LoggerConfig

import abc
import dataclasses
import logging
import typing as t
from pathlib import Path

import databind.json
import yaml
from databind.core.annotations import collect_unknowns

logger = logging.getLogger(__name__)
T_ApplicationConfig = t.TypeVar('T_ApplicationConfig', bound='ApplicationConfig')


@dataclasses.dataclass
class ApplicationConfig:
  """
  Base class for application configurations.
  """

  logging: LoggerConfig = dataclasses.field(default_factory=LoggerConfig)


class ConfigLoader(abc.ABC, t.Generic[T_ApplicationConfig]):

  @abc.abstractmethod
  def load_config(self) -> T_ApplicationConfig: ...

  @abc.abstractmethod
  def changed(self) -> bool: ...


class DatabindConfigLoader(ConfigLoader[T_ApplicationConfig]):
  """
  Default configuration loader implementation.
  """

  def __init__(
    self,
    model: t.Type[T_ApplicationConfig],
    filename: str = 'var/conf/application.yml',
    encoding: str = 'utf8',
    allow_unknown_keys: bool = False,
  ) -> None:
    assert issubclass(model, ApplicationConfig), model
    self.model = model
    self.filename = Path(filename)
    self.encoding = encoding
    self.allow_unknown_keys = allow_unknown_keys
    self.last_load_mtime: t.Optional[float] = None

  def load_config(self) -> T_ApplicationConfig:
    data = yaml.safe_load(self.filename.read_text(encoding=self.encoding))
    unknowns = collect_unknowns()
    annotations = [unknowns] if self.allow_unknown_keys else []
    config = databind.json.load(data, self.model, filename=str(self.filename), annotations=annotations)
    if unknowns.entries:
      logger.warning('Found unknown configuration keys in "%s": %s', self.filename, unknowns.entries)
    self.last_load_mtime = self.filename.stat().st_mtime
    return config

  def changed(self) -> bool:
    if self.last_load_mtime is None:
      return True
    try:
      return self.filename.stat().st_mode > self.last_load_mtime
    except FileNotFoundError:
      return True
