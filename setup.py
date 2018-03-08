import io
import os
import setuptools
import sys

if any('dist' in x for x in sys.argv):
  import setuptools_readme
  setuptools_readme.convert('README.md', encoding='utf8')
if os.path.isfile('README.rst'):
  with io.open('README.rst', encoding='utf8') as fp:
    long_description = fp.read()
    del fp
else:
  long_description = ''

with open('requirements.txt') as fp:
  reqs = fp.readlines()

setuptools.setup(
  name='bundler',
  version='0.0.2',
  license='MIT',
  url='https://github.com/NiklasRosenstein/py-bundler',
  author='Niklas Rosenstein',
  author_email='rosensteinniklas@gmail.com',
  description='Bundle the modules of a Python application. (WIP)',
  long_description=long_description,
  packages=setuptools.find_packages(),
  install_requires=reqs,
  entry_points=dict(
    console_scripts=[
      'python-bundler{d} = bundler.main:_entry_point'.format(d=d)
      for d in ('', sys.version[0], sys.version[:3])
    ]
  )
)
