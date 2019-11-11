
import io
import re
import setuptools

with io.open('src/nr/date.py', encoding='utf8') as fp:
  version = re.search(r"__version__\s*=\s*'(.*)'", fp.read()).group(1)

with io.open('README.md', encoding='utf8') as fp:
  long_description = fp.read()

setuptools.setup(
  name = 'nr.date',
  version = version,
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'Fast date parsing with timezone offset support.',
  long_description = long_description,
  long_description_content_type = 'text/markdown',
  url = 'https://github.com/NiklasRosenstein/python-nr.date',
  license = 'MIT',
  install_requires = ['python-dateutil'],
  packages = setuptools.find_packages('src'),
  package_dir = {'': 'src'},
)
