
"""
This test file extracts all Python snippets from the README file and runs
them as test cases.
"""

import os
import re
import six

def create_snippet_test(filename, line_offset, name, snippet):
  name = 'test_' + name
  def test_func():
    code = compile('\n' * line_offset + snippet, filename, 'exec')
    six.exec_(code, {})
  test_func.__name__ = name
  globals()[name] = test_func


readme_file = os.path.normpath(os.path.join(__file__, '../../../README.md'))
with open(readme_file) as fp:
  readme = fp.read()

expr = re.compile('```python(.*?)```', re.S)
offset = 0
index = 0
while True:
  match = expr.search(readme, offset)
  if not match: break
  offset = match.end()
  line_offset = readme[:match.start()].count('\n') + 1
  create_snippet_test(
    readme_file,
    line_offset,
    'readme_snippet_' + str(index),
    match.group(1).strip()
  )
  index += 1
