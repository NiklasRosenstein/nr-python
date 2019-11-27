
from setuptools import setup, find_packages

setup(
  name='nr.interface',
  version='0.9.0.dev0',
  packages=find_packages('src', exclude=['test*']),
  package_dir={'': 'src'},
  install_requires=['six', 'nr.commons', 'nr.collections', 'nr.metaclass']
)
