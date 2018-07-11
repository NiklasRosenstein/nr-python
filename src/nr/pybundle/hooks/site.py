
import sys
sys.frozen = True

PREFIXES = []
ENABLE_USER_SITE = False
USER_SITE = ''
USER_BASE = None

import builtins
import _sitebuiltins

builtins.quit = _sitebuiltins.Quitter('quit', 'CTRL-Z plus Return')
builtins.exit = _sitebuiltins.Quitter('exit', 'CTRL-D (i.e. EOF)')
builtins.help = _sitebuiltins._Helper()
