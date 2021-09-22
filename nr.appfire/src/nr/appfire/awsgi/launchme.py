
"""
Launcher for ASGI/WSGI applications that are based on the #AWSGIApplication class. Note that this launcher
file does not have the ability to respect any of the #AWSGIApplicationConfig.server options. These are
handled on a higher level by the #AWSGIApplicationLauncher.

Example:

    $ APPFIRE_HOME=my-app/ APPFIRE_APP=my_app.app:MyApp uvicorn nr.appfire.awsgi.launchme:app
"""

import os
import importlib

from . import AWSGIApplication

home = os.environ.pop('APPFIRE_HOME', None)
if home is not None:
  os.chdir(home)

entrypoint = os.environ.pop('APPFIRE_APP', None)
module_name, class_name = entrypoint.split(':')
module = importlib.import_module(module_name)
class_ = getattr(module, class_name)

if not issubclass(class_, AWSGIApplication):
  raise RuntimeError(f'{entrypoint!r} is not an AWSGIApplication subclass')

application = class_()
application.initialize()
app = application.get_application()
