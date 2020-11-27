# This file was auto-generated by Shut. DO NOT EDIT
# For more information about Shut, check out https://pypi.org/project/shut/

from __future__ import print_function
import io
import os
import setuptools
import sys

readme_file = 'README.md'
if os.path.isfile(readme_file):
  with io.open(readme_file, encoding='utf8') as fp:
    long_description = fp.read()
else:
  print("warning: file \"{}\" does not exist.".format(readme_file), file=sys.stderr)
  long_description = None

requirements = [
  'nr.metaclass >=0.0.4,<1.0.0',
  'nr.stream >=0.0.2,<1.0.0',
]
test_requirements = [
  'pytest',
]

setuptools.setup(
  name = 'nr.sumtype',
  version = '0.0.3',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'Sumtypes in Python.',
  long_description = long_description,
  long_description_content_type = 'text/markdown',
  url = 'https://git.niklasrosenstein.com/NiklasRosenstein/nr',
  license = 'MIT',
  py_modules = ['nr.sumtype'],
  package_dir = {'': 'src'},
  include_package_data = True,
  install_requires = requirements,
  extras_require = {},
  tests_require = test_requirements,
  python_requires = None,
  data_files = [],
  entry_points = {},
  cmdclass = {},
  keywords = [],
  classifiers = [],
  zip_safe = True,
  options = {
    'bdist_wheel': {
      'universal': True,
    },
  },
)
