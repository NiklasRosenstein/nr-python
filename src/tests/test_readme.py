
"""
This test file extracts all Python snippets from the README file and runs
them as test cases.
"""

import bs4
import logging
import os
import pytest
import re
import six
import sys


def create_test(filename, line_offset, name, snippet, pymin):
  """
  Creates a test for a snippet of code in the *filename* at the specified
  *line_offset*. The test function will be added to the global scope. The
  *name* must be unique.
  """

  name = 'test_' + name
  if name in globals():
    raise RuntimeError('{!r} already exists'.format(name))

  def test_func():
    code = compile('\n' * line_offset + snippet, filename, 'exec')
    six.exec_(code, {})

  if pymin is not None:
    parts = tuple(map(int, pymin.split('.')))
    test_func = pytest.mark.skipif(sys.version_info < parts,
      reason='requires Python {} or higher'.format(pymin))(test_func)

  test_func.__name__ = name
  globals()[name] = test_func


def parse_readme():
  """
  Parses the README file and extracts the Python code snippets.

  The way it is parsed is by looking for all HTML nodes that have a
  `doctest` attribute. Inside this HTML node, a Markdown enclosed code
  block with the Python language annotation is searched.

  The HTML node may also specify a minimum Python version with the `pymin`
  attribute.
  """

  expr = re.compile('```python(.*?)```', re.S)
  filename = os.path.normpath(os.path.join(__file__, '../../../README.md'))

  with open(filename) as fp:
    content = fp.read()

  soup = bs4.BeautifulSoup(content, 'html.parser')
  for idx, node in enumerate(soup.findAll(None, {'doctest': True})):
    name = str(node.attrs.get('name', u'{:0>2}'.format(idx)))
    pymin = node.attrs.get('pymin')
    match = expr.search(node.text)
    if not match:
      raise RuntimeError('found HTML node in README with doctest but no code')
    code = match.group(1)
    # TODO @NiklasRosenstein Find a way to have BeautifulSoup track line numbers?
    index = content.find(code)
    assert index >= 0
    line_offset = content[:index].count('\n')
    create_test(filename, line_offset, name, code, pymin)


parse_readme()
