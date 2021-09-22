
"""
The #nr.appfire.application defines an opinionated framework for applications. The framework defines

* configuration
* initialization sequence
* health checks
* logging configuration
"""

import abc
import logging
import typing as t

from nr.refreshable import Refreshable

from .config import ApplicationConfig, ConfigLoader, DatabindConfigLoader, T_ApplicationConfig

logger = logging.getLogger(__name__)
T_Application = t.TypeVar('T_Application', bound='Application')


class Application(abc.ABC, t.Generic[T_ApplicationConfig]):
  """
  Abstract representation of an application which has a YAML configuration file under `var/conf/application.yml`.
  The configuration model class is an argument to the #Application constructor, but it must be a subclass of the
  #ApplicationConfig model.
  """

  model_class: t.ClassVar[T_ApplicationConfig]

  def __init__(self, config_loader: t.Optional[ConfigLoader[T_ApplicationConfig]] = None) -> None:
    """
    Create a new instance of the application. The *config_loader* argument can only be omitted if the *config_model*
    class variabl is set on the subclass.
    """

    if config_loader is None:
      if not hasattr(self, 'model_class'):
        raise RuntimeError(f'missing config_loader argument to {type(self).__name__()}() or model_class class variable')
      config_loader = DatabindConfigLoader(self.model_class)

    self._config: t.Optional[Refreshable[T_ApplicationConfig]] = None
    self._config_loader = config_loader

  @property
  def config(self) -> Refreshable[T_ApplicationConfig]:
    """
    Return the application configuration as a #Refreshable.
    """

    if self._config is None:
      self.reload_config()
      assert self._config is not None
    return self._config

  def reload_config(self) -> None:
    """
    Reload the application configuration.
    """

    config = self._config_loader.load_config()
    assert isinstance(config, ApplicationConfig), (type(self._config_loader), type(config))
    if self._config is None:
      self._config = Refreshable(config)
    else:
      self._config.update(config)

  def initialize(self) -> None:
    """
    Called to initialize the application. This is the place where logging is configured, database connections
    are established and other things. The default implementation installs the logging configuration.
    """

    # TODO (@NiklasRosenstein): Start automatic config reloader thread
    self.config.get().logging.install()
