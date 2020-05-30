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

import types
from six.moves import range

__all__ = ['GenericMeta', 'Generic']


class GenericMeta(type):
  """
  This metaclass allows it's instance classes to act as a template. The
  template can then be instantiated with a subscriping syntax or the
  #instantiate() function.

  Example:

  >>> from nr.collections.generic import GenericMeta
  >>> class MyTemplate(metaclass=GenericMeta):
  ...   def __generic_init__(cls, template_param):
  ...     self.template_param = template_param
  ...   def test(self, value):
  ...     return self.template_param(value)
  >>> IntInstance = MyTemplate[int]
  >>> IntInstance().test('42')
  42

  Note that inheriting from the #Generic class is a shorthand to setting
  the metaclass to #GenericMeta (and more easily Python 2/3 compatible).
  """

  def __new__(cls, name, bases, attrs):
    if '__generic_init__' in attrs:
      attrs['__generic_init__'] = classmethod(attrs['__generic_init__'])
    bind_args, bind_kwargs = attrs.pop('__generic_bind__', (None, None))

    self = super(GenericMeta, cls).__new__(cls, name, bases, attrs)
    if bind_args is not None or bind_kwargs is not None:
      self.__generic_init__(*bind_args, **bind_kwargs)
      self.__is_generic__ = False
    else:
      self.__is_generic__ = True
    return self

  def __getitem__(self, args):
    if not isinstance(args, tuple):
      args = (args,)
    return instantiate(self, *args)


Generic = GenericMeta('Generic', (object,), {
  '__generic_init__': lambda: None
})


def instantiate(generic, *args, **kwargs):
  if '__generic_cache__' in vars(generic):
    cache = generic.__generic_cache__
  else:
    cache = generic.__generic_cache__ = {}

  key = (args, tuple(kwargs.items()))
  if key in cache:
    return cache[key]

  def _format(x):
    if isinstance(x, type):
      return x.__name__
    elif callable(x) and hasattr(x, '__name__'):
      return x.__name__ + '()'
    else:
      return repr(x)
  name = generic.__name__ + '['
  if args:
    name += ', '.join(map(_format, args))
    if kwargs:
      name += ', '
  if kwargs:
    name += ', '.join(map('{}={}'.format(k, _format(v)) for k, v in kwargs.items()))
  name += ']'

  cls = type(name, (generic,), {'__generic_bind__': (args, kwargs)})
  cache[key] = cls
  return cls
