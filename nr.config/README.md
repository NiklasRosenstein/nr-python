
> Note: This package is in the dangerous land of `0.x.y` versions and may be subject to breaking
> changes with minor version increments.

# nr.config

The `nr.config` package helps with configuration file processing and dynamic reloading tasks.
It can serve as a generic library or give you a fast and easy framework.

## Quickstart

The `nr.config.process_config()` function is the main function for processing config data. It
expects the data to process as well as a number of processor plugins that will run over config.
A common pattern is to use a `conf` section to hydrate variables for the remainder of the
configuration.

```py
from nr.config import process_config
from nr.config.plugins import Vars
import yaml

with open('var/conf/runtime.yaml') as fp:
  data = yaml.safe_load(fp)

config = process_config(data['runtime'], Vars({'conf': data['conf']}))
```

This particular example allows the use of references in the `runtime` block.

```yaml
conf:
  value: 42
runtime:
  answer: '{{conf.value}}'
```

Service applications may want to reload the configuration file whenever it changes. For this
purpose the `nr.config` module provides the `ConfigReloadTask` that uses the `watchdog` module
to observe file changes and reload the config when the file changes. Errors that occur during
the reload are automatically logged and the last valid configuration will be returned.

```py
from nr.config.reloader import ConfigReloadTask
from nr.proxy import Proxy

reload_task = ConfigReloadTask('var/conf/runtime.yaml', load_config_from_file)
reload_task.reload_callback(callback)
reload_task.start()
config = Proxy(reload_task.get)
```

---

<p align="center">Copyright &copy; 2020 Niklas Rosenstein</p>
