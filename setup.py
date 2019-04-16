
import io
import re
import setuptools
import sys

sys.path.append('src')
from nr.bundler.utils import system

with open('src/nr/bundler/__init__.py') as fp:
    version = re.search(r"__version__\s*=\s*'(.*)'", fp.read()).group(1)

with io.open('README.md') as fp:
  readme = fp.read()

requirements = {
  '*': [
    'distlib>=0.2.7',
    'nr.fs>=1.2.0',
    'nr.types>=2.0.0',
  ],
  'win': [
    'appdirs>=1.4.3',
    'pefile>=2017.11.5'
  ]
}

setuptools.setup(
  name = 'nr.bundler',
  version = version,
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'Bundle the modules of a Python application. (WIP)',
  long_description = readme,
  long_description_content_type = 'text/markdown',
  url = 'https://github.com/NiklasRosenstein/python-nr.bundler',
  license = 'MIT',
  packages = setuptools.find_packages('src'),
  package_dir = {'': 'src'},
  install_requires = requirements['*'] + requirements.get(system.name, []),
  extras_require = {
    'win': requirements['win']
  },
  entry_points = {
    'nr.cli.commands': [
      'python-bundler = nr.bundler.main:main',
    ]
  }
)
