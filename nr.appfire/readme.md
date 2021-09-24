# nr.appfire

Appfire is a toolkit that provides utilities for quickly building configurable microservices.

## Examples

### ASGI / WSGI applications

Using the `Application` class, your application is immediately configurable through a `var/conf/app.yml` file. It
always comes with a logging configuration which, by default, logs to `var/log/app.log`. The `Application.initialize()`
method gives you a chance to initialize global application state, if necessary, while having access to the your
application configuration. The configuration can be extended by using a `@dataclass` and setting
`Application.config_class`.

```py
from dataclasses import dataclass
from nr.appfire.application import Application
from nr.appfire.config import ApplicationConfig
from nr.appfire.awsgi import AWSGIAppProvider, launch

from .views import app
from .db import init_database

class MyConfig(ApplicationConfig):
  host: str = 'localhost'
  port: int = 8000
  database_url: str = 'sqlite:///var/data/db.sqlite'

class MyApp(Application, AWSGIAppProvider):

  def initialize(self) -> None:
    super().initalize()
    config = self.config.get()
    init_database(config.database_url)

  def get_app(self):
    return app

if __name__ == '__main__':
  config = MyApp().config.get()
  launch(MyApp, 'uvicorn', host=config.host, port=config.port)
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
