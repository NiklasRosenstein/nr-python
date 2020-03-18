
import io
import re
import setuptools
import sys

with io.open('src/nr/databind/core/__init__.py', encoding='utf8') as fp:
  version = re.search(r"__version__\s*=\s*'(.*)'", fp.read()).group(1)

with io.open('README.md', encoding='utf8') as fp:
  long_description = fp.read()

requirements = ['nr.collections >=0.0.1,<0.1.0', 'nr.interface >=0.0.1,<0.1.0', 'nr.stream >=0.0.1,<0.1.0', 'nr.pylang.utils >=0.0.1,<0.1.0']
extras_require = {}
extras_require['test'] = ['pytest', 'PyYAML']
tests_require = []
tests_require = ['pytest', 'PyYAML']

setuptools.setup(
  name = 'nr.databind.core',
  version = version,
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'Bind structured data directly to typed objects.',
  long_description = long_description,
  long_description_content_type = 'text/markdown',
  url = 'https://git.niklasrosenstein.com/NiklasRosenstein/nr-python-libs',
  license = 'MIT',
  packages = setuptools.find_packages('src', ['test', 'test.*', 'docs', 'docs.*']),
  package_dir = {'': 'src'},
  include_package_data = False,
  install_requires = requirements,
  extras_require = extras_require,
  tests_require = tests_require,
  python_requires = None, # TODO: '>=2.7,<3.0.0|>=3.4,<4.0.0',
  data_files = [],
  entry_points = {
    'nr.databind.core.union.test_entrypoints': [
      'int = test_union_type:Integer',
      'string = test_union_type:String',
    ]
  },
  cmdclass = {},
  keywords = [],
  classifiers = [],
)
