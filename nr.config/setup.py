# automatically created by shore 0.0.25

import io
import re
import setuptools
import sys

with io.open('src/nr/config/__init__.py', encoding='utf8') as fp:
  version = re.search(r"__version__\s*=\s*'(.*)'", fp.read()).group(1)

with io.open('README.md', encoding='utf8') as fp:
  long_description = fp.read()

requirements = ['nr.collections >=0.0.1,<1.0.0', 'nr.pylang.utils >=0.0.1,<0.1.0', 'six >=1.14.0,<2.0.0']
extras_require = {}
extras_require['reloader'] = ['watchdog >=0.10.2,<0.11.0']
extras_require['test'] = ['PyYAML']
tests_require = []
tests_require = ['PyYAML']

setuptools.setup(
  name = 'nr.config',
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
  include_package_data = True,
  install_requires = requirements,
  extras_require = extras_require,
  tests_require = tests_require,
  python_requires = None, # TODO: '>=3.4,<4.0.0',
  data_files = [],
  entry_points = {},
  cmdclass = {},
  keywords = [],
  classifiers = [],
)
