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

from nr.types.interface import Interface, attr, default


class IStructField(Interface):
  """
  Interface that describes the field of a struct.

  Implementations of this interface are assigned an "instance index"
  automatically, which allows sorting a set of fields in the order of
  instantiation.
  """

  __INSTANCE_INDEX_COUNTER = 0
  instance_index = attr(int, default=None)

  #: The priority determines when the field will have its chance to
  #: extract values from the source dictionary. The default priority
  #: is zero (0).
  priority = attr(int, default=0)

  #: The name of the field represents the name of the attribute that is
  #: assigned to the Struct object. This name may be assigned to the
  #: field at a later point, when it becomes known, with the [[bind()]]
  #: method.
  name = attr(typing.Optional[str], default=None)

  #: The datatype of the field. This represents the expected value that
  #: ends up in the object and usually represents the structure from
  #: which it can be extracted as well (but this is not the case for
  #: [[ObjectKeyField]] and [[WildcardField]]).
  datatype = attr(IDataType)

  #: If `True`, indicates that the field is derived from some other place.
  #: Usually this means that the field does not end up in the stored
  #: version of the [[Object]] the same way a standard [[Field]] does.
  derived = attr(bool)

  #: `True` if the field is required. This field has no default value and
  #: must be set by an implementation.
  required = attr(bool)

  classdef.comparable('priority name datatype derived required',
                       decorate=default)

  def __init__(self):
    self.instance_index = IFieldDescriptor.__INSTANCE_INDEX_COUNTER
    IFieldDescriptor.__INSTANCE_INDEX_COUNTER += 1
    self.priority = 0
    self.name = None
    self.derived = False

  @default
  def bind(self, name):  # type: str -> None
    if self.name is not None:
      raise RuntimeError('cannot set field name to {!r}, name is already '
                         'set to {!r}'.format(name, self.name))
    if not isinstance(name, str):
      raise TypeError('IFieldDescriptor.name must be a string, got {}'
                      .format(type(name).__name__))
    self.name = name

  @default
  def get_class_member_value(self, object_cls):  # type: (Type[Object]) -> Any
    """
    This method is called when the field is accessed via
    [[Object.__getattr__()]] and can be used to expose a class-level property
    on the [[Object]] class.

    Return [[NotSet]] if no property is to be exposed.

    The default implementation checks if the [[.datatype]] is an instance of
    [[ObjectType]] and returns the wrapped [[Object]] subclass in that case.
    """

    if isinstance(self.datatype, ObjectType):
      return self.datatype.object_cls
    return NotSet

  def get_default_value(self):  # type: () -> Any
    # raises: NotImplementedError
    pass

  def extract_kwargs(self, object_cls, locator, kwargs, handled_keys):
    # type: (Type[Object], Locator, Dict[str, Any], Set[str]) -> None
    """
    This method is called from the [[ObjectType.extract()]] method to
    compose the [[Object]] keyword arguments for construction.

    The field must specify the keys from [[Locator.value()]] that were
    treated in this method to prevent an error for an extract key if
    [[META.EXTRACT_STRICT]] is set.
    """
