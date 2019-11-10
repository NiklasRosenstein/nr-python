
import textwrap

from nr.types.struct import CustomCollection, Struct, Field, JsonObjectMapper, deserialize
from nr.types.struct.contrib.yaml import load_with_line_numbers


def test_load_with_line_numbers():
  class Item(Struct):
    name = Field(str)
    value = Field(int)

  class Items(CustomCollection, list):
    item_type = Item

  yaml_code = textwrap.dedent('''
    ---
    - name: foo
      value: 42
    - name: bar
      value: 99
  ''')

  mapper = JsonObjectMapper(options={'track_location': True})
  payload = load_with_line_numbers(yaml_code, filename='<string>')
  items = deserialize(mapper, payload, Items)

  assert items.__location__.value.__metadata__ == {'filename': '<string>', 'lineno': 2}
  assert items[0].__location__.value.__metadata__ == {'filename': '<string>', 'lineno': 3}
  assert items[1].__location__.value.__metadata__ == {'filename': '<string>', 'lineno': 5}
