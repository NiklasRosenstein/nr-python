
import io
import re
import setuptools
import sys

with io.open('src/nr/databind/__init__.py', encoding='utf8') as fp:
  version = re.search(r"__version__\s*=\s*'(.*)'", fp.read()).group(1)

with io.open('README.md', encoding='utf8') as fp:
  long_description = fp.read()

requirements = ['nr.interface >=0.1.0,<0.2.0']
test_requirements = ['pytest', 'PyYAML']

setuptools.setup(
  name = 'nr.databind',
  version = version,
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'Bind structured data directly to typed objects.',
  long_description = long_description,
  long_description_content_type = 'text/markdown',
  url = 'https://git.niklasrosenstein.com/NiklasRosenstein/nr-python-libs',
  license = 'MIT',
  packages = setuptools.find_packages('src'),
  package_dir = {'': 'src'},
  include_package_data = False,
  install_requires = requirements,
  tests_require = test_requirements,
  python_requires = None, # TODO: '>=2.7,<3.0.0|>=3.4,<4.0.0',
  entry_points = {
    'nr.databind.core.struct.Mixin': [
      'json = nr.databind.json:JsonMixin',
      'tuple = nr.databind.contrib.mixins.tuple:TupleMixin',
    ]
  }
)
