# automatically created by shore

import io
import re
import setuptools
import sys

with io.open('src/nr/databind/rest/__init__.py', encoding='utf8') as fp:
  version = re.search(r"__version__\s*=\s*'(.*)'", fp.read()).group(1)

with io.open('README.md', encoding='utf8') as fp:
  long_description = fp.read()

requirements = ['nr.collections >=0.1.0,<1.0.0', 'nr.interface >=0.0.2,<1.0.0', 'nr.databind.core >=0.0.5,<0.1.0', 'nr.databind.json >=0.0.5,<0.1.0', 'nr.pylang.utils >=0.0.1,<0.1.0', 'nr.sumtype >=0.0.2,<0.1.0']

setuptools.setup(
  name = 'nr.databind.rest',
  version = version,
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'Package description here.',
  long_description = long_description,
  long_description_content_type = 'text/markdown',
  url = 'https://git.niklasrosenstein.com/NiklasRosenstein/nr-python-libs',
  license = 'MIT',
  packages = setuptools.find_packages('src', ['test', 'test.*', 'docs', 'docs.*']),
  package_dir = {'': 'src'},
  include_package_data = False,
  install_requires = requirements,
  extras_require = {},
  tests_require = [],
  python_requires = None, # TODO: '>=3.4,<4.0.0',
  data_files = [],
  entry_points = {},
  cmdclass = {},
  keywords = [],
  classifiers = [],
)
