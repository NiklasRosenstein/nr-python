# nr.utils.wsgi

Utilities for writing WSGI applications.

## Contents

### WSGI App Runners

Depending on the environment (e.g. production vs. development), the way your Python WSGI
application is started may be different. The `runners` module can help you start your
Python application the right way for the right environment. Furthermore, it works with
the `nr.databind.core` package, allowing you to configure runners in a configuration file.

Example:

```yml
bind: localhost:8000
entrypoint: my_application.wsgi:app
files: ./var
runners:
  prod:
    type: gunicorn
    num_workers: 4
  dev:
    type: flask
    debug: true
```

Then in your Python script or command-line tool to invoke your application:

```py
from nr.utils.wsgi.config import WsgiAppConfig
config = WsgiAppConfig.load('app-config.yaml')
config.run(runner='dev', daemonize=True)
```

Without loading a configuration from a YAML file, you can still use the runners from code:

```py
from nr.utils.wsgi.runners import WsgiAppConfig, GunicornRunner

runner = GunicornRunner(num_workers=4)
runner.run(WsgiAppConfig('my_application.wsgi:app'), daemonize=True)
```
