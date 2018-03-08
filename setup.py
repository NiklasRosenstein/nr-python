import os
import sys
from setuptools import find_packages, setup

def readme():
  if os.path.isfile('README.md') and any('dist' in x for x in sys.argv[1:]):
    if os.system('pandoc -s README.md -o README.rst') != 0:
      print('-----------------------------------------------------------------')
      print('WARNING: README.rst could not be generated, pandoc command failed')
      print('-----------------------------------------------------------------')
      if sys.stdout.isatty():
        input("Enter to continue... ")
    else:
      print("Generated README.rst with Pandoc")

  if os.path.isfile('README.rst'):
    with open('README.rst') as fp:
      return fp.read()
  return ''

setup(
  name='bundler',
  version='0.0.1',
  license='MIT',
  url='https://github.com/NiklasRosenstein/py-bundler',
  author='Niklas Rosenstein',
  author_email='rosensteinniklas@gmail.com',
  description='Bundle the modules of a Python application. (WIP)',
  long_description=readme(),
  packages=find_packages(),
  entry_points=dict(
    console_scripts=[
      'python-bundler{d} = bundler.main:_entry_point'.format(d=d)
      for d in ('', sys.version[0], sys.version[:3])
    ]
  )
)
