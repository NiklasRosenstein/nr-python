from setuptools import find_packages, setup

setup(
  name='twister',
  author='Niklas Rosenstein',
  author_email='rosensteinniklas@gmail.com',
  version='0.0.1',
  packages=find_packages(),
  entry_points=dict(
    console_scripts=[
      'twister = twister.main:_entry_point'
    ]
  )
)
