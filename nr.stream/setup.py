
import io
import re
import setuptools
import sys

with io.open('src/nr/stream.py', encoding='utf8') as fp:
  version = re.search(r"__version__\s*=\s*'(.*)'", fp.read()).group(1)

long_description = None

requirements = ['nr.collections >=0.0.1,<1.0.0', 'nr.pylang.utils >=0.0.1,<1.0.0', 'six >=1.11.0,<2.0.0']

setuptools.setup(
  name = 'nr.stream',
  version = version,
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'Use iterators like Java streams.',
  long_description = long_description,
  long_description_content_type = 'text/plain',
  url = 'https://git.niklasrosenstein.com/NiklasRosenstein/nr-python-libs',
  license = 'MIT',
  packages = setuptools.find_packages('src', ['test', 'test.*', 'docs', 'docs.*']),
  package_dir = {'': 'src'},
  include_package_data = False,
  install_requires = requirements,
  extras_require = {},
  tests_require = [],
  python_requires = None, # TODO: '>=2.6,<3.0.0|>=3.4,<4.0.0',
  data_files = [],
  entry_points = {},
  cmdclass = {},
  keywords = [],
  classifiers = [],
)
