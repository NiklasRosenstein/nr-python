
import setuptools
import io

with io.open('README.md') as fp:
  readme = fp.read()

with io.open('requirements.txt') as fp:
  requirements = fp.readlines()

setuptools.setup(
  name = 'nr.pybundle',
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
  install_requires = requirements
)
