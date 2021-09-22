
"""
Configuration for Python loggers.
"""

import abc
import dataclasses
import dataclasses
import enum
import logging
import logging.handlers
import sys
import typing as t
import warnings
from pathlib import Path

from databind.core.annotations import union

logger = logging.getLogger(__name__)


@union(
  union.Subtypes.entrypoint('nr.appfire.application.config.logging.FormatterConfig'),
  style=union.Style.flat)
@dataclasses.dataclass
class FormatterConfig(abc.ABC):

  @abc.abstractmethod
  def get_formatter(self) -> logging.Formatter: ...


@union(
  union.Subtypes.entrypoint('nr.appfire.application.config.logging.HandlerConfig'),
  style=union.Style.flat)
@dataclasses.dataclass
class HandlerConfig(abc.ABC):

  level: t.Optional['LogLevel'] = None
  formatter: t.Optional['FormatterConfig'] = None

  @abc.abstractmethod
  def _get_handler(self) -> logging.Handler: ...

  def get_handler(self, default_formatter: logging.Formatter) -> logging.Handler:
    handler = self._get_handler()
    if self.level is not None:
      handler.level = self.level.value
    if self.formatter is not None:
      handler.setFormatter(self.formatter.get_formatter())
    elif not handler.formatter:
      handler.setFormatter(default_formatter)
    return handler


@dataclasses.dataclass
class StandardFormatterConfig(FormatterConfig):
  """
  Configuration for #logging.Formatter.
  """

  fmt: t.Optional[str] = None
  datefmt: t.Optional[str] = None
  style: str = '%'
  validate: bool = True

  def get_formatter(self) -> logging.Formatter:
    args = []
    if not sys.version < '3.8' and self.validate:
      args.append(self.validate)
    return logging.Formatter(self.fmt, self.datefmt, self.style, *args)


@dataclasses.dataclass
class FileHandlerConfig(HandlerConfig):
  """
  Configuration for #logging.FileHandler and #logging.RotatingFileHandler.
  """

  # FileHandler
  filename: str = t.cast(str, None)
  mode: str = 'a'
  delay: bool = False
  encoding: t.Optional[str] = None
  errors: t.Optional[str] = None

  # RotatingFileHandler
  max_bytes: t.Optional[int] = None
  backup_count:int = 0

  create_dirs: bool = True

  def __post_init__(self) -> None:
    if self.filename is None:
      raise ValueError(f'FileHandlerConfig.filename must be set')

  def _get_handler(self) -> logging.Handler:
    args = []
    if self.errors is not None:
      if sys.version < '3.9':
        warnings.warn('FileHandlerConfig.errors is set but only supported starting Python 3.9')
      else:
        args.append(self.errors)

    filename = Path(self.filename)
    if self.create_dirs and not filename.parent.exists():
      filename.parent.mkdir(parents=True)

    if self.max_bytes is None:
      return logging.FileHandler(str(filename), self.mode, self.encoding, self.delay, *args)
    else:
      return logging.handlers.RotatingFileHandler(str(filename), self.mode, self.max_bytes, self.backup_count,
        self.encoding, self.delay, *args)


class LogLevel(enum.Enum):
  NOTSET = logging.NOTSET
  DEBUG = logging.DEBUG
  INFO = logging.INFO
  WARNING = logging.WARNING
  ERROR = logging.ERROR
  CRITICAL = logging.CRITICAL


@dataclasses.dataclass
class LoggerConfig:
  """
  Logging configurations.
  """

  #: Root log level.
  level: LogLevel = LogLevel.INFO

  #: Overrides for individual loggers.
  level_overrides: t.Dict[str, LogLevel] = dataclasses.field(default_factory=dict)

  #: Define root logger handlers.
  handlers: t.List[HandlerConfig] = dataclasses.field(default_factory=lambda: get_default_handlers())

  #: Default formatter that a handler config may inherit.
  default_formatter: FormatterConfig = dataclasses.field(default_factory=lambda: get_default_formatter())

  def install(self, replace: bool = True) -> None:
    logger.info('Installing logging configuration')
    if replace:
      logging.root.handlers.clear()
      logging.root.filters.clear()
    logging.root.setLevel(self.level.value)
    default_formatter = self.default_formatter.get_formatter()
    for handler in self.handlers:
      logging.root.addHandler(handler.get_handler(default_formatter))
    for logger_name, level in self.level_overrides.items():
      logging.getLogger(logger_name).setLevel(level.value)


def get_default_handlers() -> t.List[HandlerConfig]:
  """
  Returns the default handler configuration.
  """

  return [
    FileHandlerConfig(filename='var/log/application.log', max_bytes=1024 * 1024 * 128, backup_count=10)
  ]


def get_default_formatter() -> FormatterConfig:
  """
  Returns the default formatter configuration.
  """

  return StandardFormatterConfig('[%(asctime)s - %(levelname)s - %(name)s]: %(message)s')
