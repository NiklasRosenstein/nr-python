# automatically created by shore 0.0.23

import io
import re
import setuptools
import sys

with io.open('src/nr/pylang/bundle/__init__.py', encoding='utf8') as fp:
  version = re.search(r"__version__\s*=\s*'(.*)'", fp.read()).group(1)

with io.open('README.md', encoding='utf8') as fp:
  long_description = fp.read()

requirements = ['distlib >=0.2.7,<1.0.0', 'nr.databind.core >=0.0.1,<0.1.0', 'nr.fs >=1.3.1,<2.0.0', 'nr.sumtype >=0.0.1,<1.0.0', 'nr.stream >=0.0.1,<1.0.0', 'tqdm >=4.42.1,<5.0.0']
if sys.platform.startswith('win32'):
  requirements += ['appdirs >=1.4.3,<2.0.0', 'pefile >=2017.11.5']

setuptools.setup(
  name = 'nr.pylang.bundle',
  version = version,
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'Create standalone Python applications.',
  long_description = long_description,
  long_description_content_type = 'text/markdown',
  url = 'https://git.niklasrosenstein.com/NiklasRosenstein/nr-python-libs',
  license = 'MIT',
  packages = setuptools.find_packages('src', ['test', 'test.*', 'docs', 'docs.*']),
  package_dir = {'': 'src'},
  include_package_data = True,
  install_requires = requirements,
  extras_require = {},
  tests_require = [],
  python_requires = None, # TODO: '>=2.7,<3.0.0|>=3.4,<4.0.0',
  data_files = [],
  entry_points = {
    'console_scripts': [
      'nr-pylang-bundle = nr.pylang.bundle.__main__:_entrypoint_main',
    ]
  },
  cmdclass = {},
  keywords = [],
  classifiers = [],
)
