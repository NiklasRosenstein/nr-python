import sys
from setuptools import find_packages, setup

setup(
  name='bundler',
  author='Niklas Rosenstein',
  author_email='rosensteinniklas@gmail.com',
  description='Bundle the modules of a Python application. (WIP)',
  version='0.0.1',
  packages=find_packages(),
  entry_points=dict(
    console_scripts=[
      'python-bundler{d} = bundler.main:_entry_point'.format(d=d)
      for d in ('', sys.version[0], sys.version[:3])
    ]
  )
)
