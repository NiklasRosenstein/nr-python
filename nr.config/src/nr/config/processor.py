# -*- coding: utf8 -*-
# Copyright (c) 2020 Niklas Rosenstein
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

from nr.collections import abc
from nr.pylang.utils.classdef import make_singleton
from typing import List, Union
import copy
import os
import re
import six

#: This is a special singleton return by #parse_accessor_string() to represent
#: a wildcard index.
WILDCARD = make_singleton('WILDCARD')


def parse_accessor_string(s):  # type: (str) -> List[Union[str, int, WILDCARD]]
  """
  Parses an a string consisting of a sequence of access instructions and returns it
  as a list of keys and indices.

  >>> from nr.config.plugins import parse_accessor_string
  >>> parse_accessor_string('a.b[0].c')
  ['a', 'b', 0, 'c']
  >>> parse_accessor_string('a[*].b')
  ['a', WILDCARD, 'b']
  """

  result = []
  for part in s.split('.'):
    match = re.match(r'(.*)\[(\d+|\*)\]', part)
    if match:
      result.append(match.group(1))
      result.append(WILDCARD if match.group(2) == '*' else int(match.group(2)))
    else:
      result.append(part)

  return result


def resolve_accessor_list(l, data):  # type: (List[Union[str, int, WILDCARD]], Any) -> Any
  """
  Resolves a list of access instructions on *data* and returns the value.
  """

  it = iter(l)
  for item in it:
    if item == WILDCARD:
      # TODO: Verify that *item* is a sequence?
      subl = list(it)
      data = [resolve_accessor_list(subl, v) for v in data]
      break
    else:
      data = data[item]

  return data


class Vars(object):
  """
  A preprocessor plugin that substitutes strings of the form `{{variableName}}`
  with the actual value that they reference. References that encompass the full
  string can be expanded into values of other types. References as part of a
  longer strings will be rendered in that part of the string.
  """

  _DEFAULT_REGEX = r'\{\{([^}]+)\}\}'

  def __init__(self, iterable=None, resolve=None, regex=None, safe=False):
    """
    :param iterable: Used to create a new #dict() if specified. Cannot be used at
      the same time as *resolve*.
    :param resolve: Resolve the text inside `{{...}}` to return a replacement
      value. If not specified, the default implementation will be used (using
      #parse_accessor_string() and #resolve_accessor_list().
    :param regex: The regex to match variables. The regex must have exactly one
      group defined (the name of the variable).
    :param safe: If True, KeyError or IndexError exceptions raised by *resolver*
      will be caught and the substitution will not occur.
    """

    if iterable is not None:
      if resolve is not None:
        raise TypeError('iterable and resolve cannot be specified together')
      data = dict(iterable)
      resolver = lambda key: resolve_accessor_list(parse_accessor_string(key), self._data)
    else:
      data = None

    self._data = data
    self._resolver = resolver
    self._regex = re.compile(regex or self._DEFAULT_REGEX)
    self._safe = safe

  def __sub(self, match):
    " Private. Passed to #re.sub() for replacements. "

    key = match.group(1)
    try:
      return self._resolver(key)
    except (KeyError, IndexError):
      if self._safe:
        return match.group(0)
      raise

  def __call__(self, data):
    if isinstance(data, six.string_types):
      match = self._regex.match(data)
      if match and match.group(0) == data:
        return self.__sub(match)
      else:
        return self._regex.sub(self.__sub, data)
    return data


class Include(object):
  """
  Replaces strings of the form `{{!include <FILENAME>}}` with the contents of
  the actual file, optionally loaded with the specified *load_func*.
  """

  def __init__(self, base_dir, load_func=None):
    self.base_dir = base_dir
    self.load_func = load_func

  def __call__(self, data):
    if not isinstance(data, six.string_types):
      return data
    match = re.match(r'{{\s*!include\s+(.+?)\s+}}$', data)
    if not match:
      return data
    filename = os.path.join(self.base_dir, match.group(1))
    with open(filename) as fp:
      if self.load_func:
        return self.load_func(fp)
      return fp.read()


class Envvars(object):
  """
  Replaces references of `{{ env VARIABLE_NAME }}` with the actual environment
  variable value.
  """

  def __init__(self, resolve=None):
    if resolve is None:
      resolve = lambda k: os.environ[k]
    self._resolve = resolve

  def __call__(self, data):
    if not isinstance(data, six.string_types):
      return data
    def sub(match):
      envname = match.group(1)
      return self._resolve(match.group(1))
    return re.sub(r'{{\s*env\s+([\w_\d]+)\s*}}', sub, data)


class Processor(object):
  """
  Encapsulates plugins and some options and then allows processing nested
  data recursively.
  """

  def __init__(self, plugins=(), mutate=False, keep_type=True):
    self._plugins = list(plugins)
    self._mutate = mutate
    self._keep_type = keep_type

  def add_plugin(self, plugin):
    self._plugins.append(plugin)

  def __call__(self, data):
    """
    Process the specified *data* with the list of *plugins* and return the
    result. Handles strings, mappings and sequences. If the *mutate* is True,
    mappings and sequences will be assumed mutable. If *keep_type* is True, the
    function will attempt to keep the same type of the mapping or sequence,
    otherwise dicts or lists are returned.
    """

    for plugin in self._plugins:
      data = plugin(data)

    if isinstance(data, abc.Mapping):
      if self._mutate and isinstance(data, abc.MutableMapping):
        for key in data:
          data[key] = self(data[key])
      else:
        cls = type(data) if self._keep_type else dict
        data = cls((k, self(data[k])) for k in data)
    elif isinstance(data, abc.Sequence) and not isinstance(data, six.string_types):
      if self._mutate and isinstance(data, abc.MutableSequence):
        for index, value in enumerate(data):
          data[index] = self(value)
      else:
        cls = type(data) if self._keep_type else list
        data = cls(self(v) for v in data)

    return data


def process_config(data, plugins):
  return Processor(plugins)(data)
