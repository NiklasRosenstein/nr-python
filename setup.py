# -*- coding: utf8 -*-
# Copyright (c) 2019 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

import io
import os
import re
import setuptools
import sys
from setuptools.command.install import install

with io.open('src/nr/types/__init__.py', encoding='utf8') as fp:
  version = re.search(r"__version__\s*=\s*'(.*)'", fp.read()).group(1)

with io.open('README.md', encoding='utf8') as fp:
  readme = fp.read()


class Verify(install):
  description = 'Checks if the version number matches CIRCLE_TAG'

  def run(self):
    tag = os.getenv('CIRCLE_TAG')
    if tag != 'v{}'.format(version):
      info = "error: CIRCLE_TAG={!r} does not match 'v{}'".format(tag, version)
      sys.exit(info)


setuptools.setup(
  name = 'nr.types',
  version = version,
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'Toolbox with useful Python classes and type magic.',
  long_description = readme,
  long_description_content_type = 'text/markdown',
  url = 'https://github.com/NiklasRosenstein/python-nr.types',
  license = 'MIT',
  packages = setuptools.find_packages('src'),
  package_dir = {'': 'src'},
  install_requires = ['six', 'typing'],
  extras_require = {
    'test': ['pytest', 'pytest-cov'],
    'full': ['PyYAML'],
    'persist': ['nr.fs >= 1.5.0']
  },
  cmdclass = {
    'verify': Verify
  }
)
