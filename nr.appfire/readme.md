# nr.appfire

Appfire is a toolkit that provides utilities for quickly building configurable microservices.

## Examples

### ASGI / WSGI applications

Using the `AWSGIApp` class, your application is immediately configurable through a `var/conf/app.yml` file. It
always comes with a logging configuration which, by default, logs to `var/log/app.log`. The `initialize()` method
gives you a chance to initialize global application state, if necessary, while having access to the your application
configuration. The configuration can be extended by using a `@dataclass`.

```py
from dataclasses import dataclass, field
from nr.appfire.config import ApplicationConfig
from nr.appfire.awsgi import AWSGIApp, AWSGILauncher, UvicornLauncher

from .views import app
from .db import init_database

@dataclass
class MyConfig(ApplicationConfig):
  launcher: AWSGILauncher = field(default_factory=lambda: UvicornLauncher(host='localhost', port='8000'))
  host: str = 'localhost'
  port: int = 8000
  database_url: str = 'sqlite:///var/data/db.sqlite'

class MyApp(AWSGIApp[MyConfig], config_class=MyConfig):

  def initialize(self) -> None:
    super().initalize()
    init_database(self.config.get().database_url)

  def get_awsgi_app(self):
    return app

if __name__ == '__main__':
  MyApp().launch)
```

### Background tasks

```py
import dataclasses
from nr.appfire.tasks import Runnable, Task, DefaultExecutor

@dataclasses.dataclass
class Looper(Runnable[None]):
  loops: int

  def run(self, task: Task[None]) -> None:
    for i in range(self.loops):
      print(i)
      if not task.sleep(1):
        print('Bye, bye')
        break

executor = DefaultExecutor('MyApp')
executor.execute(Looper(10))
executor.idlejoin()
```

---

<p align="center">Copyright &copy; 2021 Niklas Rosenstein</p>
