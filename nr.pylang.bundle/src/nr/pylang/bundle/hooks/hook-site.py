
import os

def inspect_module(module):
  if module.name != 'site': return
  #module.filename = os.path.join(os.path.dirname(__file__), 'site.py')
  #module.load_imports()
