
from nr.config.jinja import load_yaml_files, Environment


def test_render_01():
  payload = {
    'conf': {'group-name': 'Administrators'},
    'users': [{'username':'admin', 'group': '{{ conf["group-name"] }}'}],
  }
  config = Environment().render(payload, {})
  assert config['users'][0]['group'] == 'Administrators'
