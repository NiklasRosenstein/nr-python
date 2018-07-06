
import setuptools

setuptools.setup(
  name = 'nr.fs',
  version = '1.0.1',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'Filesystem and path manipulation tools.',
  url = 'https://github.com/NiklasRosenstein-Python/nr.fs',
  license = 'MIT',
  namespace_packages = ['nr'],
  packages = setuptools.find_packages('src'),
  package_dir = {'': 'src'}
)
