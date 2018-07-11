
import os
import sys
sys.frozen = True
sys.frozen_env = {}
# We assume that lib/ is right inside the application directory.
sys.frozen_env['application_dir'] = os.path.dirname(os.path.dirname(__file__))
sys.frozen_env['resource_dir'] = os.path.join(sys.frozen_env['application_dir'], 'res')

PREFIXES = []
ENABLE_USER_SITE = False
USER_SITE = ''
USER_BASE = None

import builtins
import _sitebuiltins

builtins.quit = _sitebuiltins.Quitter('quit', 'CTRL-Z plus Return')
builtins.exit = _sitebuiltins.Quitter('exit', 'CTRL-D (i.e. EOF)')
builtins.help = _sitebuiltins._Helper()
