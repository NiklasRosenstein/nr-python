
from nr.config.yaml import load as load_yaml


def test_load():
  yaml_code = '''
    a:
      b:
      - 1
      - 2
      c: [3, 4]
  '''
  data = load_yaml(yaml_code)
  assert data['a'].lineno == 2
  assert data['a']['b'].lineno == 3
  assert data['a']['c'].lineno == 6
