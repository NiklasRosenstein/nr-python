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
Some common utility functions for working with the [[nr.types.structured]]
module.
"""

from ..object import Field, MetadataField, Object


class OriginInfo(Object):
  filename = Field(str)
  lineno = Field(int)


def add_origin_metadata_field(field_name='origin'):
  """
  A decorator for [[Object]] subclasses that adds an "origin" metadata field
  that extracts a "filename" and "lineno" key from the metadata (if present).
  """

  def getter(metadata):
    return OriginInfo(metadata.get('filename'), metadata.get('lineno'))

  def decorator(object_cls):
    object_cls.__fields__.update([
      MetadataField(OriginInfo, getter=getter, name=field_name)
    ])
    return object_cls

  return decorator


__all__ = ['add_origin_metadata_field']
