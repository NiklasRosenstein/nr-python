
import os
import sys
sys.frozen = True
sys.frozen_env = {}

# Find the application root directory.
app_dir = os.path.dirname(__file__)
while not os.path.exists(os.path.join(app_dir, 'runtime')):
  app_dir = os.path.dirname(app_dir)

# We assume that lib/ is right inside the application directory.
sys.frozen_env['app_dir'] = app_dir
sys.frozen_env['lib_dir'] = os.path.join(app_dir, 'lib')
sys.frozen_env['runtime_dir'] = os.path.join(app_dir, 'runtime')
sys.frozen_env['resource_dir'] = os.path.join(app_dir, 'res')

PREFIXES = []
ENABLE_USER_SITE = False
USER_SITE = ''
USER_BASE = None

import builtins
import _sitebuiltins

builtins.quit = _sitebuiltins.Quitter('quit', 'CTRL-Z plus Return')
builtins.exit = _sitebuiltins.Quitter('exit', 'CTRL-D (i.e. EOF)')
builtins.help = _sitebuiltins._Helper()
