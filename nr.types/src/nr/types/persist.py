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

"""
This module focuses on tools for persistable program state.
"""

from nr.fs import isfile, remove, atomic_file

from nr.types.interface import Interface, implements
from nr.types.singletons import NotSet


class IPersister(Interface):

    def meaningful_default(self):  # type: () -> Any
        pass

    def binary(self):  # type: () -> bool
        pass

    def load(self, fp):  # type: (File) -> Any
        pass

    def save(self, fp, data):  # type: (File, Any) -> None
        pass


@implements(IPersister)
class JsonPersister(object):

    persister_name = 'json'

    def __init__(self, **options):
        import json
        self._json = json
        self._options = options

    def meaningful_default(self):
        return {}

    def binary(self):
        return False

    def load(self, fp):
        return self._json.load(fp)

    def save(self, fp, data):
        return self._json.dump(data, fp, **self._options)


def get_persister(persister):
    if IPersister.provided_by(persister):
        return persister
    elif isinstance(persister, type) and IPersister.implemented_by(persister):
        return persister()
    elif isinstance(persister, str):
        for impl in IPersister.implementations():
            if getattr(impl, 'persister_name', None) == persister:
                return impl()
    raise TypeError('unable to get a persister for {!r}'.format(persister))


class Persistable(object):
    """
    Represents a persistable object.
    """

    def __init__(self, persister, filename, lazy=True, default=NotSet):
        self.persister = get_persister(persister)
        self.filename = filename
        self._raw_data = NotSet
        self.default = default

        if not lazy:
            self.raw_data

    def __call__(self):
        """
        Returns the data represented by this persistable object. If the data
        is not yet loaded, it will be loaded from file.
        """

        if self._raw_data is NotSet:
            mode = 'rb' if self.persister.binary() else 'r'
            if isfile(self.filename):
                with open(self.filename, mode) as fp:
                    self._raw_data = self.persister.load(fp)
            else:
                if self.default is NotSet:
                    self._raw_data = self.persister.meaningful_default()
                elif callable(self.default):
                    self._raw_data = self.default()
                else:
                    self._raw_data = self.default
        return self._raw_data

    @property
    def raw_data(self):
        """
        Same as [#$__call__()]].
        """

        return self()

    @raw_data.setter
    def raw_data(self, value):
        self._raw_data = value

    def persist(self):
        """
        Persists the object to file. If the raw data is [[NotSet]], the file
        will be deleted instead.

        The data will be persisted in an atomic fashion: It will first be
        written to a temporary file and afterwards used to replace the
        existing file.
        """

        if self._raw_data is NotSet:
            if isfile(self.filename):
                remove(self.filename)
        else:
            with atomic_file(self.filename, text=not self.persister.binary()) as fp:
                self.persister.save(fp, self._raw_data)
