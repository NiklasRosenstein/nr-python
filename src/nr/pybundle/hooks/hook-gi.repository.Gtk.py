
import os
import sys


def collect_data(module, bundle):
  print('@@@', module)
  if module.name != 'gi.repository.Gtk':
    return

  # TODO: Determine if GTK Adwait Icons actually need to be
  #       included, or maybe none or another theme's icons.

  bundle.add_resource(
    os.path.join(sys.prefix, 'share', 'themes', 'Default'),
    'share/themes/Default')
  bundle.add_resource(
    os.path.join(sys.prefix, 'share', 'icons', 'Adwaita'),
    'share/icons/Adwaita')

  if not bundle.get_site_snippet('gi.repository.Gtk'):
    bundle.add_site_snippet('gi.repository.Gtk',
      "os.environ['GTK_DATA_PREFIX'] = sys.frozen_env['app_dir']")
