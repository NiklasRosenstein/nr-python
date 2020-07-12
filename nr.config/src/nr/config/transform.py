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

from .util import AccessorList
from collections import abc
from typing import Any, Callable, List, Optional, Union
import re
import six

Key = Union[int, str]
ValueTransformFunc = Callable[[Any], Any]


class BoxedValue:
  """
  Represents a value with context.
  """

  def __init__(self, parent: Optional['BoxedValue'], key: Optional[Key], value: Any):
    self.parent = parent
    self.key = key
    self.value = value

  @property
  def path(self) -> str:
    items = ('.' + k if isinstance(k, str) else '[{}]'.format(k) for k in self.path_list)
    return '$' + ''.join(items)

  @property
  def accessor_list(self) -> AccessorList:
    result = []
    while self and self.key:
      result.append(self.key)
      self = self.parent
    result.reverse()
    return AccessorList(result)

  def __getitem__(self, key: Key) -> 'BoxedValue':
    return BoxedValue(self, key, self.value[key])


class ValueTransformer:
  """
  A value transformer is an object that takes an arbitrary value and some contextual
  information and may transform that into a different value. BoxedValue transfomers are
  applied recursively on a nested data structure with the #Transformer class.
  """

  def transform_value(self, value: Any, context: BoxedValue) -> Any:
    """
    Return an arbitrary value in place of *value*. Note that #BoxedValue.value always
    references the original value in the config, not any in-between state in the middle
    of applying multiple #ValueTransformer#s.
    """

    raise NotImplementedError


class LambdaValueTransformer(ValueTransformer):

  def __init__(self, func: ValueTransformFunc) -> None:
    self.func = func

  def transform_value(self, value: Any, context: BoxedValue) -> Any:
    return self.func(value)


class VariableResolver:
  """
  Base class for objects that resolve variables for a #Substitution transformer.
  """

  def resolve(self, variable: str, context: BoxedValue) -> Any:
    raise NotImplementedError


class DefaultVariableResolver(VariableResolver):
  """
  Resolves variables in the specified nested data structure *data*. If *relative* is enabled,
  variable names are treated relative to their own position in the currently transformed
  data structure.
  """

  def __init__(self, data: Any, relative: bool = False) -> None:
    self.data = data
    self.relative = relative

  def resolve(self, variable: str, context: BoxedValue) -> Any:
    accessor = AccessorList(variable)
    if self.relative:
      accessor = context.parent.accessor_list + accessor
    try:
      return accessor(self.data)
    except (KeyError, IndexError):
      raise KeyError(variable)


class Substitution(ValueTransformer):
  """
  Implements variable substitution on string values it finds that adhere to a specific
  format. The default format is `{{variable_name}}`. If the variable is resolved to a
  a string, the variable reference may be prefixed or suffixed with other content.

  Otherwise the variable reference must be the full value and will be substituted in place.
  """

  class Error(Exception):
    pass

  _DEFAULT_REGEX = r'\{\{([^}]+)\}\}'

  def __init__(self, regex: str = None, default_value: Any = None) -> None:
    self.regex = re.compile(regex or self._DEFAULT_REGEX)
    self.default_value = default_value
    self.resolvers = []

  def register(self, variable_resolver: VariableResolver) -> 'Substitution':
    self.resolvers.append(variable_resolver)
    return self

  def with_vars(self, data: Any, relative: bool = False) -> 'Substitution':
    return self.register(DefaultVariableResolver(data, relative))

  def _resolve(self, variable: str, context: BoxedValue) -> Any:
    for resolver in self.resolvers:
      try:
        return resolver.resolve(variable, context)
      except KeyError:
        pass
    raise KeyError(variable)

  def _transform_string(self, value: str, context: BoxedValue) -> str:
    try:
      new_value = self._resolve(value, context)
    except KeyError:
      return ''
    if not isinstance(new_value, str):
      raise Substitution.Error(
        'cannot substitute variable {!r} with value of type "{}" in string'
        .format(value, type(new_value).__name__))
    return new_value

  def transform_value(self, value: Any, context: BoxedValue):
    if not isinstance(value, str):
      return value

    match = self.regex.search(value)
    if not match:
      return value

    if match.group(0) != value:
      return self.regex.sub(lambda m: self._transform_string(m.group(1), context), value)

    try:
      return self._resolve(match.group(1), context)
    except KeyError:
      return self.default_value


class Transformer:
  """
  A collection of #ValueTransformer objects that applies them recursively on a nested
  data structure.

  # Arguments
  value_transformers: The #ValueTransformer objects for this transformer.
  inplace: Whether to modify mappings and sequences in place.
  retain_type: If *inplace* is `False`, retain the mapping and list type or coerce
    to dicts and lists instead.
  """

  def __init__(
    self,
    *value_transformers: ValueTransformer,
    inplace: bool = False,
    retain_type: bool = True,
  ) -> None:
    self.value_transformers = list(value_transformers)
    self.inplace = inplace
    self.retain_type = retain_type

  def register(self, value_transformer: ValueTransformer) -> None:
    self.value_transformers.append(value_transformer)

  def register_func(self, transform_func: ValueTransformFunc) -> None:
    self.value_transformers.append(LambdaValueTransformer(transform_func))

  def _transform(self, context: BoxedValue) -> Any:
    value = context.value
    for vt in self.value_transformers:
      value = vt.transform_value(value, context)

    context.value = value

    if isinstance(value, abc.Mapping):
      if self.inplace and isinstance(value, abc.MutableMapping):
        for key in value:
          value[key] = self._transform(context[key])
      else:
        cls = type(value) if self.retain_type else dict
        value = cls((k, self._transform(context[k])) for k in value)
    elif isinstance(value, abc.Sequence) and not isinstance(value, six.string_types):
      if self.inplace and isinstance(value, abc.MutableSequence):
        for index in range(len(value)):
          value[index] = self._transform(context[index])
      else:
        cls = type(value) if self.retain_type else list
        value = cls(self._transform(context[i]) for i in range(len(value)))

    return value

  def transform(self, data: Any) -> Any:
    return self._transform(BoxedValue(None, None, data))

  def __call__(self, data: Any) -> Any:
    """
    Alias for #transform().
    """

    return self.transform(data)
