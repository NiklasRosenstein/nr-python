
import setuptools
import io

with io.open('README.md') as fp:
  readme = fp.read()

with io.open('requirements.txt') as fp:
  requirements = fp.readlines()

setuptools.setup(
  name = 'nr.bundler',
  version = '1.0.0',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'Bundle the modules of a Python application. (WIP)',
  long_description = readme,
  long_description_content_type = 'text/markdown',
  url = 'https://gitlab.niklasrosenstein.com/NiklasRosenstein/python/nr.pybundle',
  license = 'MIT',
  namespace_packages = ['nr'],
  packages = setuptools.find_packages('src'),
  package_dir = {'': 'src'},
  install_requires = [
    'appdirs>=1.4.3',
    'distlib>=0.2.7',
    'pefile>=2017.11.5',
    'nr.gitignore>=1.0.0',
    'nr.fs>=1.0.2',
    'nr.types>=1.0.6',
  ],
  entry_points = {
    'nr.cli.commands': [
      'python-bundler = nr.bundler.main:main',
    ]
  }
)
