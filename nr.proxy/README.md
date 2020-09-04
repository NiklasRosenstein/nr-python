# nr.proxy

The `nr.proxy` module provides utilities for creating Python object proxies which will forward
almost any interaction with the object to another object. This allows for the creation of very
convenient APIs in Python applications (e.g. à la Flask `request` object).

This package requires Python 3.5 or higher.

  [1]: https://sqlalchemy.org/
  [2]: https://click.palletsprojects.com/

## Example: `proxy`

Command-line interfaces built with [Click][2] can use the `Context.ensure_object()` method to
attach information to a context. Retrieving that information from the context include a couple
of lines which over all reduce the readability of the code. Using a `proxy` allows you to access
that information once it is initialized in the context as if the data was available globally.

```py
import click
import nr.proxy
from pathlib import Path
from .config import Configuration

config = nr.proxy.proxy[Configuration](lambda: click.get_current_context().obj['config'])

@click.group()
@click.option('-c', '--config', 'config_file', type=Path, default='config.toml',
  default='Path to the configuration file.')
@click.pass_context
def cli(ctx: click.Context, config: Path) -> None:
  ctx.ensure_object(dict)['config'] = Configuration.load(config)

@cli.command()
def validate():
  # No need to use @click.pass_context or access ctx.obj['config'].
  config.validate()
```

## Example: `threadlocal`

The below is an example for creating a globally accessible [SqlAlchemy][1] session. Inside a
with-context using `make_session()`, the global `session` object can be accesses like a normal
instance of the `Session` class. Outside of the context, accessing the `session` object results
in a `RuntimeError` with the specified error message.

The advantage of this method is that the `Session` object does not need to be passed around,
but can instead just be accessed globally.

```py
import contextlib
import nr.proxy
from sqlalchemy.orm import sessionmaker
from typing import Generator

Session = sessionmaker()
session = nr.proxy.threadlocal[Session](
  name=__name__ + '.session',
  error_message=
    '({name}) No SqlAlchemy session is available. Ensure that you are using the '
    'make_session() context manager before accessing the global session proxy.',
)

@contextlib.contextmanager
def make_session() -> Generator[None, None, None]:
  """
  A context manager that creates a new #Session object and makes it available in the global
  #session proxy object.
  """

  nr.proxy.push(session, Session())
  try:
    yield
  except:
    session.rollback()
    raise
  else:
    session.commit()
  finally:
    nr.proxy.pop(session)
```

---

<p align="center">Copyright &copy; 2020 Niklas Rosenstein</p>
