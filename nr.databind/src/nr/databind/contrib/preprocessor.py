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
configuration files with the struct module, as well as dynamically loading
configurable objects (ie. dynamically resolved structs).


## Preprocessor

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

## IConfigurable

Todo
"""

import copy
import re
import six

from nr.collections import abc


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


__all__ = [
  'Preprocessor',
  'preprocess',
  'IConfigurable',
  'import_configurable',
  'load_configurable'
]
