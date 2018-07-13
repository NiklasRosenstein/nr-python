
import os

def module_found(module):
  if module.name != 'site': return
  module.filename = os.path.join(os.path.dirname(__file__), 'site.py')
