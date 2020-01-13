
import os
import sys


def collect_data(module, bundle):
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

  bundle.add_resource(
    os.path.join(sys.prefix, 'lib', 'gdk-pixbuf-2.0', '2.10.0'),
    'lib/gdk-pixbuf-2.0/2.10.0')

  if not bundle.get_site_snippet('gi.repository.Gtk'):
    bundle.add_site_snippet('gi.repository.Gtk',
      "os.environ['GTK_DATA_PREFIX'] = sys.frozen_env['app_dir']")

  if not bundle.get_rthook('gi.repository.Gtk'):
    bundle.add_rthook('gi.repository.Gtk',
      "from gi.repository import Gtk\n"
      "Gtk.IconTheme.get_default().prepend_search_path(os.path.join(sys.frozen_env['app_dir'], 'share/icons'))\n"
      "os.environ['GDK_PIXBUF_MODULE_FILE'] = os.path.join(sys.frozen_env['app_dir'], 'lib/gdk-pixbuf-2.0/2.10.0/loaders.cache')")
