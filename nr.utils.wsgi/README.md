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
app:
  bind: localhost:8000
  entrypoint: my_application.wsgi:app
runners:
  - env: prod
    type: gunicorn
    gunicorn:
      num_workers: 4
  - env: dev
    type: flask
    flask:
      debug: true
```

Then in your Python script or command-line tool to invoke your application:

```py
from nr.utils.wsgi.runners import IWsgiRunner
from nr.utils.wsgi.config import WsgiAppConfiguration

config = WsgiAppConfiguration.load('app-config.yaml')
config.run(env='dev', daemonize=True)
```

Without loading a configuration from a YAML file, you can still use the runners from code:

```py
from nr.utils.wsgi.runners import WsgiAppConfig, GunicornRunner

runner = GunicornRunner(num_workers=4)
runner.run(WsgiAppConfig('my_application.wsgi:app'), daemonize=True)
```
