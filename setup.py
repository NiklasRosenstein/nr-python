
import io
import setuptools

with io.open('README.md', encoding='utf8') as fp:
  readme = fp.read()

setuptools.setup(
  name = 'nr.types',
  version = '2.0.0',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'Provides a number os useful data types for day-to-day Python programming.',
  long_description = readme,
  long_description_content_type = 'text/markdown',
  url = 'https://github.com/NiklasRosenstein/python-nr.types',
  license = 'MIT',
  packages = setuptools.find_packages('src'),
  package_dir = {'': 'src'},
  install_requires = ['six'],
  extras_require = {
    'test': ['pytest', 'pytest-cov', 'BeautifulSoup4']
  }
)
