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
from nr.databind.contrib.config import preprocess
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
from nr.databind.core import Struct, Field, ObjectMapper
from nr.databind.json import JsonModule
class RootConfig(Struct):
  runtime = Field({
    "media": Field({
      "path": Field(str)
    })
  })
config = ObjectMapper(JsonModule()).deserialize(data, RootConfig)
```

What the [[preprocess()]] function shown above does can also be done manually
like so:

```py
import yaml
from nr.databind.contrib.config import Preprocessor
data = yaml.safe_load(filename)
preprocessor = Preprocessor()
preprocessor['$serviceRoot'] = os.path.dirname(__file__)
preprocessor.flat_update(preprocessor(data.pop('config', {})))
data = preprocessor(data)
```
"""

import copy
import os
import re
import six

from nr.collections import abc


class Vars(dict):
  """ A preprocessor plugin that substitutes variables in strings of the form
  `{{variableName}}`. This class is a mapping that describes the known
  variables for the substition. """

  _DEFAULT_REGEX = r'\{\{([^}]+)\}\}'

  def __init__(self, iterable=None, regex=None):
    super(Vars, self).__init__(iterable or ())
    self.regex = re.compile(regex or self._DEFAULT_REGEX)

  def __sub(self, match):
    """ The method that is passed to [[re.sub()]]. Private. """

    key = match.group(1)
    try:
      return self[key]
    except KeyError:
      return '{{' + key + '}}'

  def __call__(self, data):
    if isinstance(data, six.string_types):
      return self.regex.sub(self.__sub, data)
    return data

  def __repr__(self):
    return 'Vars({})'.format(super(Vars, self).__repr__())

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


class Include(object):
  """ Replaces strings of the form `{{!include <FILENAME>}}` with the contents
  of the actual file, optionally loaded with the specified *load_func*. """

  def __init__(self, base_dir, load_func=None):
    self.base_dir = base_dir
    self.load_func = load_func

  def __call__(self, data):
    if not isinstance(data, six.string_types):
      return data
    match = re.match(r'{{\s*!include\s+(.+?)\s+}}$', data)
    if not match:
      return data
    filename = os.path.join(self.base_dir, match.group(1))
    with open(filename) as fp:
      if self.load_func:
        return self.load_func(fp)
      return fp.read()


class Envvars(object):
  """ Replaces references of `{{ env VARIABLE_NAME }}` with the actual
  environment variable value. If the environment vair """

  def __init__(self, resolve=None):
    if resolve is None:
      resolve = lambda k: os.environ[k]
    self._resolve = resolve

  def __call__(self, data):
    if not isinstance(data, six.string_types):
      return data
    def sub(match):
      envname = match.group(1)
      return self._resolve(match.group(1))
    return re.sub(r'{{\s*env\s+([\w_\d]+)\s*}}', sub, data)


class Preprocessor(object):

  def __init__(self, plugins=(), mutate=False, keep_type=True):
    self._plugins = list(plugins)
    self._mutate = mutate
    self._keep_type = keep_type

  def add_plugin(self, plugin):
    self._plugins.append(plugin)

  def __call__(self, data):
    """ Process the specified *data* with the list of *plugins* and return the
    result. Handles strings, mappings and sequences. If the *mutate* is True,
    mappings and sequences will be assumed mutable. If *keep_type* is True, the
    function will attempt to keep the same type of the mapping or sequence,
    otherwise dicts or lists are returned. """

    for plugin in self._plugins:
      data = plugin(data)

    if isinstance(data, abc.Mapping):
      if self._mutate and isinstance(data, abc.MutableMapping):
        for key in data:
          data[key] = self(data[key])
      else:
        cls = type(data) if self._keep_type else dict
        data = cls((k, self(data[k])) for k in data)
    elif isinstance(data, abc.Sequence) and not isinstance(data, six.string_types):
      if self._mutate and isinstance(data, abc.MutableSequence):
        for index, value in enumerate(data):
          data[index] = self(value)
      else:
        cls = type(data) if self._keep_type else list
        data = cls(self(v) for v in data)

    return data


def preprocess(data, *args, **kwargs):
  preprocessor = Preprocessor(*args, **kwargs)
  return preprocessor(data)


def config_preprocess(config, runtime, plugins=(), *args, **kwargs):
  """ Preprocesses a configuration in two phases: First *config* is
  pre-processed and then used to enrich the #Vars plugin. Second the
  *runtime* is pre-processed with the new variables made available from
  the *config* object.

  If no #Vars plugin exists in *plugins*, it as appended automatically. """

  plugins = list(plugins)
  vars_plugin = next((x for x in plugins if isinstance(x, Vars)), None)

  if vars_plugin is None:
    vars_plugin = Vars()
    plugins.append(vars_plugin)

  preprocessor = Preprocessor(plugins)
  vars_plugin.flat_update(preprocessor(config))
  return preprocessor(runtime)


__all__ = [
  'Vars',
  'Include',
  'Preprocessor',
  'preprocess',
  'config_preprocess'
]
