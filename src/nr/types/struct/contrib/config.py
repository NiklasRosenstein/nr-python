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

""" This module provides a basis for easily describing YAML or JSON
configuration files with the struct module.

Example configuration:

```yaml
config:
  directories:
    data: '{{$serviceRoot}}/data'
runtime:
  media:
   path: '{{directories.data}}/media'
```

Loading this type of configuration is as simple as this:

```py
import yaml
from nr.types.struct.contrib.config import preprocess
data = preprocess(
  yaml.safe_load(filename),
  init_variables={'$serviceRoot': os.path.dirname(__file__)},
  config_key='config'
)
```

Now *data* contains no longer the *config* key and contains only the processed
version of the YAML string above. It can then be easily deserialized into an
actual structure, for example:

```py
from nr.types.struct import Struct, Field, JsonObjectMapper, deserialize
class RootConfig(Struct):
  runtime = Field({
    "media": Field({
      "path": Field(str)
    })
  })
config = deserialize(JsonObjectMapper(), data, RootConfig)
```

What the [[preprocess()]] function shown above does can also be done manually
like so:

```py
import yaml
from nr.types.struct.contrib.config import Preprocessor
data = yaml.safe_load(filename)
preprocessor = Preprocessor()
preprocessor['$serviceRoot'] = os.path.dirname(__file__)
preprocessor.flat_update(preprocessor(data.pop('config', {})))
data = preprocessor(data)
```
"""

import copy
import importlib
import re
import six

from nr.types import abc
from nr.types.collections import LambdaDict
from nr.types.interface import Interface, attr, implements
from nr.types.struct import DefaultTypeMapper, ExtractTypeError, \
  ExtractValueError, InvalidTypeDefinitionError, IConverter, IDataType, \
  ITypeDefAdapter, JsonObjectMapper, Struct, UnionType, deserialize
from nr.types.utils import classdef


class Preprocessor(dict):
  """ The Preprocessor class is used to substitute variables in a nested
  structured comprised of dictionaries and lists. By default, the regex it
  uses to replace variables matches strings like `{{<variable_name>}}`.

  This class is a subclass of [[dict]]. """

  regex = re.compile(r'\{\{([^}]+)\}\}')

  def __init__(self, iterable=None, regex=None, mutate=False, keep_type=True):
    super(Preprocessor, self).__init__(iterable or ())
    self.regex = regex or Preprocessor.regex
    self.mutate = mutate
    self.keep_type = keep_type

  def __sub(self, match):
    """ The method that is passed to [[re.sub()]]. Private. """

    key = match.group(1)
    try:
      return self[key]
    except KeyError:
      return '{{' + key + '}}'

  def __call__(self, data):
    """ Process the specified *data* and return the result. Handles strings,
    mappings and sequences. If the [[#mutate]] attribute is set to True,
    mappings and sequences will be assumed mutable. If [[#keep_type]] is set
    to True, it will try to keep the same type of the mapping or sequence,
    otherwise dicts or lists are returned. """

    if isinstance(data, six.string_types):
      return self.regex.sub(self.__sub, data)
    elif isinstance(data, abc.Mapping):
      if self.mutate and isinstance(data, abc.MutableMapping):
        for key in data:
          data[key] = self(data[key])
      else:
        data = (type(data) if self.keep_type else dict)((k, self(data[k])) for k in data)
      return data
    elif isinstance(data, abc.Sequence):
      if self.mutate and isinstance(data, abc.MutableSequence):
        for index, value in enumerate(data):
          data[index] = self(value)
      else:
        data = (type(data) if self.keep_type else list)(self(v) for v in data)
      return data
    return data

  def __repr__(self):
    return 'Preprocessor({})'.format(super(Preprocessor, self).__repr__())

  def flat_update(self, mapping, separator='.'):
    """ Performs a flat update of the variables in the Preprocessor dictionary
    by concatenating nested keys with the specified separator. This is useful
    for populating the preprocessor with variables from nested structures as
    variable names are not treated as multiple keys but as-is.

    Example:

    ```py
    preprocessor.flat_update({'directory': {'data': '/opt/app/data'}})
    assert preprocessor('{{directory.data}}') == '/opt/app/data'
    ```

    ```py
    preprocessor.flat_update({'key': [{'value': 'foo'}]})
    assert preprocessor('{{key[0].value}}') == 'foo'
    """

    def update(key, value):
      if not isinstance(value, six.string_types) and isinstance(value, abc.Sequence):
        for index, item in enumerate(value):
          update(key + '[' + str(index) + ']', item)
      elif isinstance(value, abc.Mapping):
        for key2 in value:
          update((key + '.' + key2 if key else key2), value[key2])
      else:
        self[key] = value

    if not isinstance(mapping, abc.Mapping):
      raise TypeError('expected Mapping, got {}'.format(type(mapping).__name__))
    update('', mapping)


def preprocess(data, init_variables=None, config_key='config', regex=None):
  """ Convenience function to take the *config_key* from *data* and preprocess
  it, then use it to [[Preprocessor.flat_update()]] the current pre-processor
  to process the rest of *data*. Returns a copy of *data* without the
  *config_key*. """

  data = copy.copy(data)
  preprocessor = Preprocessor(init_variables, regex=regex)
  preprocessor.flat_update(preprocessor(data.pop(config_key, {})))
  return preprocessor(data)


class IConfigurable(Interface):
  """ Instances of this class can be loaded with [[load_configurable()]].
  Implementations must accept a single argument in their constructor, which
  is an instance of the class returned by [[get_configuration_model()]].
  """

  config = attr()  # Automatically set by load_configurable()

  @classmethod
  def get_configuration_model(cls):  # type: () -> Type[Struct]
    pass


@DefaultTypeMapper.register()
@implements(ITypeDefAdapter)
class IConfigurableAdapter(object):

  def adapt(self, mapper, py_type_def):
    if isinstance(py_type_def, type) and issubclass(py_type_def, IConfigurable):
      return IConfigurableType(py_type_def)
    raise InvalidTypeDefinitionError(py_type_def)


@implements(IDataType)
class IConfigurableType(object):

  classdef.comparable(['import_spec_key', 'base_interface'])

  def __init__(self, base_interface=None, import_spec_key='class', nested=False):
    assert isinstance(import_spec_key, str), type(import_spec_key)
    self.base_interface = base_interface
    self.import_spec_key = import_spec_key
    self.nested = nested

  def check_value(self, py_value):
    return py_value


@JsonObjectMapper.register()
@implements(IConverter)
class IConfigurableConverter(object):

  def accept(self, datatype):
    return type(datatype) == IConfigurableType

  def deserialize(self, mapper, location):
    if not isinstance(location.value, abc.Mapping):
      raise ExtractTypeError(location)

    datatype = location.datatype
    if datatype.import_spec_key not in location.value:
      raise ExtractValueError(location, 'missing key {!r}'.format(key))

    import_spec = location.value[datatype.import_spec_key]
    cls = import_configurable(import_spec)
    union_type = UnionType(
      types={import_spec: cls.get_configuration_model()},
      type_key=datatype.import_spec_key,
      nested=datatype.nested)
    config = mapper.deserialize(location.replace(datatype=union_type))
    return load_configurable(cls, config, datatype.base_interface)

  def serialize(self, mapper, location):
    if not IConfigurable.provided_by(location.value):
      raise ExtractTypeError(location)

    datatype = location.datatype
    key = datatype.import_spec_key
    import_spec = type(location.value).__module__ + ':' + \
      type(location.value).__name__

    union_type = UnionType(
      types={import_spec: location.value.get_configuration_model()},
      type_key=datatype.import_spec_key,
      nested=datatype.nested)

    data = mapper.serialize(location.replace(value=location.value.config, datatype=union_type))
    return data


def import_configurable(import_spec, base_interface=None):
  module, name = import_spec.rpartition(':')[::2]
  module = importlib.import_module(module)
  cls = getattr(module, name)

  if base_interface and not base_interface.implemented_by(cls):
    raise RuntimeError('{!r} does not implemented {}'.format(
      import_spec, base_interface.__name__))

  return cls


def load_configurable(import_spec, config, base_interface=None, mapper=None):
  """ Loads a "Configurable" from an import specification (of the syntax
  `<module>:<member>`). Before the loaded implementation is instantiated,
  the function will first ensure it implements the *base_interface* (if
  provided) and then extract the configuration from the model provided
  by [[Configurable.get_configuration_model()]] with the provided *options*.
  """

  if not isinstance(import_spec, type):
    cls = import_configurable(import_spec, base_interface)
  else:
    cls = import_spec
    if base_interface and not base_interface.implemented_by(cls):
      raise RuntimeError('{!r} does not implemented {}'.format(
        import_spec, base_interface.__name__))

  if mapper is None:
    mapper = JsonObjectMapper()

  if not isinstance(config, cls.get_configuration_model()):
    config = deserialize(mapper, config, cls.get_configuration_model())

  try:
    return cls(config)
  except TypeError as exc:
    raise TypeError('{}: {}'.format(import_spec, exc))


__all__ = [
  'Preprocessor',
  'preprocess',
  'IConfigurable',
  'import_configurable',
  'load_configurable'
]
