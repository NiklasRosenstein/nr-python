# -*- coding: utf8 -*-
# Copyright (c) 2019 Niklas Rosenstein
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

""" Provides a collection and map type that is persistable to disk. """

from abc import ABCMeta
from . import abc
from six.moves import cPickle as pickle
import codecs
import json
import os
import six


class Persister(six.with_metaclass(ABCMeta)):

  def load(self, fp):  # type: (Union[BinaryIO, Any, NoneType]) -> Any
    pass

  def save(self, fp, data):  # type: (Union[BinaryIO, Any, NoneType], Any)
    pass


class _PersistableMixin(object):
  """ Mixin for persistable objects. """

  def __init__(self, persister, init_value):  # type: (Persister, Any)
    self.__persister = persister
    self._data = init_value

  def load(self, file=None):  # type: (Union[str, BinaryIO, None])
    if isinstance(file, str):
      with open(file, 'rb') as fp:
        self.load(fp)
    else:
      self._data = self.__persister.load(file)

  def save(self, file=None):  # type: (Union[str, BinaryIO, None])
    if isinstance(file, str):
      with open(file, 'wb') as fp:
        self.save(fp)
    else:
      self.__persister.save(file, self._data)


class PersistableDict(abc.MutableMapping, _PersistableMixin):

  def __init__(self, persister, *args, **kwargs):
    _PersistableMixin.__init__(self, persister, dict(*args, **kwargs))

  def __len__(self):
    return len(self._data)

  def __getitem__(self, key):
    return self._data[key]

  def __setitem__(self, key, value):
    self._data[key] = value

  def __delitem__(self, key):
    del self._data[key]

  def __iter__(self):
    return iter(self._data)


class PersistableList(abc.MutableSequence, _PersistableMixin):

  def __init__(self, persister, *args):
    _PersistableMixin.__init__(self, persister, list(*args))

  def __len__(self):
    return len(self._data)

  def __getitem__(self, index):
    return self._data[index]

  def __setitem__(self, index, value):
    self._data[index] = value

  def __delitem__(self, index):
    del self._data[index]

  def __iter__(self):
    return iter(self._data)

  def insert(self, index, value):
    return self._data.insert(index, value)


class PicklePersister(Persister):

  def load(self, fp):
    return pickle.load(fp)

  def save(self, fp, data):
    pickle.dump(data, fp)


class JsonPersister(Persister):

  def __init__(self, encoder=None, decoder=None, encoding='utf-8'):
    self.encoder = encoder
    self.decoder = decoder
    self.encoding = encoding

  def load(self, fp):
    fp = codecs.getreader(self.encoding)(fp)
    return json.load(fp)

  def save(self, fp, data):
    fp = codecs.getwriter(self.encoding)(fp)
    return json.dump(data, fp)


class FilePersister(Persister):

  def __init__(self, persister, filename, opener=None):
    self.persister = persister
    self.filename = filename
    self.opener = opener

  def load(self, fp):
    assert fp is None, "FilePersister expected no file to be passed in"
    with (self.opener or open)(self.filename, 'rb') as fp:
      return self.persister.load(fp)

  def save(self, fp, data):
    assert fp is None, "FilePersister expected no file to be passed in"
    with (self.opener or open)(self.filename, 'wb') as fp:
      self.persister.save(fp, data)

  def exists(self):
    return os.path.isfile(self.filename)
