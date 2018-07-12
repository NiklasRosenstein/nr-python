
import os
import sys
sys.frozen = True
sys.frozen_env = {}

# Find the application root directory.
application_dir = os.path.dirname(__file__)
while not os.path.exists(os.path.join(application_dir, 'runtime')):
  application_dir = os.path.dirname(application_dir)

# We assume that lib/ is right inside the application directory.
sys.frozen_env['application_dir'] = application_dir
sys.frozen_env['resource_dir'] = os.path.join(application_dir, 'res')

# TODO: For gi.repository -- The hook should actually inject this code when it is necessary.
os.environ['GI_TYPELIB_PATH'] = application_dir

PREFIXES = []
ENABLE_USER_SITE = False
USER_SITE = ''
USER_BASE = None

import builtins
import _sitebuiltins

builtins.quit = _sitebuiltins.Quitter('quit', 'CTRL-Z plus Return')
builtins.exit = _sitebuiltins.Quitter('exit', 'CTRL-D (i.e. EOF)')
builtins.help = _sitebuiltins._Helper()
