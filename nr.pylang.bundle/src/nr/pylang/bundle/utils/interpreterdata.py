
"""
This script is executed with the source Python interpreter to get various details, such as the
module path. The result is printed to stdout in JSON format.
"""

import argparse
import json
import os
import shlex
import subprocess as sp
import sys

if sys.version > '3.4':
  from typing import Any, Dict, List


class InterpreterData:

  def __init__(self, version, sys_path, stdlib_path):
    # type: (str, List[str], List[str]) -> None
    self.version = version
    self.sys_path = sys_path
    self.stdlib_path = stdlib_path

  def json(self):  # type: () -> Dict[str, Any]
    return {'version': self.version, 'sys_path': self.sys_path, 'stdlib_path': self.stdlib_path}

  @classmethod
  def current(cls):  # type: () -> InterpreterData

    # TODO @nrosenstein Determine all the stdlib paths. This is just a
    #      method that seems to work on OSX.
    import contextlib, _ctypes
    stdlib_path = sorted(set([
      os.path.normpath(os.path.dirname(os.__file__)),
      os.path.normpath(os.path.dirname(contextlib.__file__)),
      os.path.normpath(os.path.dirname(_ctypes.__file__)),
    ]))

    return cls(sys.version, sys.path, stdlib_path)


def get_interpreter_data(program=None):
  if program is None:
    return InterpreterData.current()
  else:
    args = shlex.split(program) + [__file__]
    output = sp.check_output(args)
    return InterpreterData(**json.loads(output))


if __name__ == '__main__':
  print(json.dumps(InterpreterData.current().json()))
