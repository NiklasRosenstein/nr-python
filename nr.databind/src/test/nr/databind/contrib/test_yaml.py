
from nr.databind.core import Collection, Struct, Field
from nr.databind.contrib.yaml import loadwsi, YamlSourceInfo
from ..fixtures import mapper
import textwrap


def test_load_with_line_numbers(mapper):
  class Item(Struct):
    name = Field(str)
    value = Field(int)

  class Items(Collection, list):
    item_type = Item

  yaml_code = textwrap.dedent('''
    ---
    - name: foo
      value: 42
    - name: bar
      value: 99
  ''')

  payload = loadwsi(yaml_code, filename='<string>')
  items = mapper.deserialize(payload, Items, decorations=[YamlSourceInfo()])

  assert items.__databind__['source_info'] == ('<string>', 2)
  assert items[0].__databind__['source_info'] == ('<string>', 3)
  assert items[1].__databind__['source_info'] == ('<string>', 5)
