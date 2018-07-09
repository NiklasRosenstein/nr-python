# Copyright (c) 2018 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

"""
Execute Python code in a separate process, automatically serializing the
result and retrieving it back as a Python object.
"""

import nr.fs
import pickle
import subprocess
import sys
import textwrap


def execute(code):
  """
  Execute a Python code snippet in a separate Python process. The return
  value of that code snippet will be returned by this function via the
  #pickle module.

  Example:

  ```python
  from nr.pybundle.utis.pysubcmd import execute
  assert execute('return 42') == 42
  """

  with nr.fs.tempfile('.py', encoding='utf8') as fp:
    fp.write('# coding: utf8\n')
    fp.write('def main():\n  ')
    fp.write('\n  '.join(textwrap.dedent(code).split('\n')))
    fp.write('\nimport pickle, sys; pickle.dump(main(), sys.stdout.buffer)\n')
    fp.close()
    return pickle.loads(subprocess.check_output([sys.executable, fp.name]))
