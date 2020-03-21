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

"""
Allows you to load YAML files with filename and lineno information in
sets, lists and dicts.
"""

from __future__ import absolute_import
import collections
import io
import types
import yaml

__all__ = ['load']


def _yaml_type_factory(name, base):
  """
  Generates a subclass for the specified *base* class where its constructor
  accepts a filename and line number as the first two arguments.
  """

  class _YamlType(base):

    def __init__(self, filename, lineno, *args, **kwargs):
      super(_YamlType, self).__init__(*args, **kwargs)
      self.filename = filename
      self.lineno = lineno

    def __repr__(self):
      return '{}({})'.format(type(self).__name__, super(_YamlType, self).__repr__())

  _YamlType.__name__ = name
  if hasattr(_YamlType, '__qualname__'):
    _YamlType.__qualname__ = name

  return _YamlType


YamlSet = _yaml_type_factory('YamlSet', set)
YamlList = _yaml_type_factory('YamlList', list)
YamlDict = _yaml_type_factory('YamlDict', dict)


class YamlLineNumberLoaderMixin(object):

  def __init__(self, filename):
    self.__filename = filename

    # Make sure the yaml_constructors are hooked up.
    self.yaml_constructors = self.yaml_constructors.copy()
    for key, value in self.yaml_constructors.items():
      if hasattr(type(self), value.__name__):
        self.yaml_constructors[key] = getattr(type(self), value.__name__)

  def compose_node(self, parent, index):
    # Propagate current line numbers to the Yaml AST nodes.
    line = self.line
    node = super(YamlLineNumberLoaderMixin, self).compose_node(parent, index)
    node.__line__ = line + 1
    return node

  def construct_mapping(self, node, deep=False):
    value = super(YamlLineNumberLoaderMixin, self).construct_mapping(node, deep=deep)
    return YamlDict(self.__filename, node.__line__, value)

  def construct_sequence(self, node, deep=False):
    value = super(YamlLineNumberLoaderMixin, self).construct_sequence(node, deep=deep)
    return YamlList(self.__filename, node.__line__, value)

  def construct_pairs(self, node, deep=False):
    value = super(YamlLineNumberLoaderMixin, self).construct_pairs(node, deep=deep)
    return YamlList(self.__filename, node.__line__, value)

  def construct_yaml_set(self, node):
    data = YamlSet(self.__filename, node.__line__)
    yield data
    value = self.construct_mapping(node)
    data.update(value)

  def construct_yaml_seq(self, node):
    data = YamlList(self.__filename, node.__line__)
    yield data
    data.extend(self.construct_sequence(node))

  def construct_yaml_map(self, node):
    data = YamlDict(self.__filename, node.__line__)
    yield data
    value = self.construct_mapping(node)
    data.update(value)


def load(_data=None, *args, **kwargs):
  """
  Loads YAML data from a file, adding line numbers to every type of collection
  returned from the loader (sets, lists and dicts). The specified YAML loader
  will be mixed with the #YamlLineNumberLoaderMixin class. The default loader
  is #yaml.SafeLoader.
  """

  loader_cls = kwargs.pop('Loader', yaml.SafeLoader)
  filename = kwargs.pop('filename', None)

  if _data is None and filename is not None:
    with io.open(filename, encoding=kwargs.pop('encoding', None)) as fp:
      _data = fp.read()

  class _YamlLoader(YamlLineNumberLoaderMixin, loader_cls):
    def __init__(self, *args, **kwargs):
      loader_cls.__init__(self, *args, **kwargs)
      YamlLineNumberLoaderMixin.__init__(self, filename)

  loader = _YamlLoader(_data, *args, **kwargs)
  return loader.get_single_data()
