
import os

def examine(finder, module, result):
  if module.name != 'site': return
  module.filename = os.path.join(os.path.dirname(__file__), 'site.py')
