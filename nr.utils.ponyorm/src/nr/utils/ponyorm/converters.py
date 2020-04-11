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

import enum
import pony.orm.dbapiprovider


# TODO(nrosenstein) How to register a converter only for an AppDatabase
class EnumConverter(pony.orm.dbapiprovider.StrConverter):
  """
  A converter for #enum.Enum values.
  """

  for_types = [enum.Enum]

  @classmethod
  def register(cls, db: pony.orm.Database):
    db.provider.converter_classes.append((enum.Enum, cls))

  def validate(self, val, obj=None):
    if not isinstance(val, enum.Enum):
      raise ValueError('mut be an Enum, got {}'.format(type(val)))
    return val

  def py2sql(self, val):
    return val.name

  def sql2py(self, value):
    # Any enum type can be used, so py_type ensures the correct one is used to create the enum instance
    return self.py_type[value]
