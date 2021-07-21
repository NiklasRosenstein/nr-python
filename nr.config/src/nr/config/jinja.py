
"""
nr.config.jinja
===============

Use Jinja2 templates in YAML values. The available variables and built-ins are resolved in the
following order:

* Built-ins provided by this module (e.g. #flatten()).
* Variables provided by the caller
* Variables in the same YAML file

Example:

```yml
conf:
  group-name: Administrators

users:
  - username: admin
    group: {{ conf['group-name'] }}
```

How to load:

```py
from nr.config.jinja import load_yaml_files, Environment
config = Environment().render(load_yaml_files(['config.yml']))
print(config['users'][0]['group'])  # Administrators
```
"""

import enum
import copy
import functools
import typing as t
import yaml

import jinja2
from nr.collections.chaindict import ChainDict

_JsonType = t.Dict[str, t.Any]
_JinjaFilter = t.Callable[..., t.Any]
T = t.TypeVar('T')
T_StructuredType = t.TypeVar('T_StructuredType', bound=t.Union[t.Dict, t.List])


class ExcludeType(enum.Enum):
  Value = 1

Exclude = ExcludeType.Value


def _filter_flatten(seq: t.Sequence[t.Union[T, t.Sequence[T]]], max_depth: int = None) -> t.List[T]:
  """
  Flatten a nested sequence, up to *max_depth*.
  """

  result = []
  for item in seq:
    if isinstance(item, t.Sequence) and (max_depth is None or max_depth > 0):
      result += flatten(item, max_depth - 1 if max_depth is not None else None)
    else:
      result.append(item)
  return result


def _map_values(val: T_StructuredType, func: t.Callable[[t.Any], t.Any]) -> T_StructuredType:
  """
  Helper function that maps *func* over the values in *val*. If *val* is a list, it will be
  called for all items in the list and the new list will be returned. For a mapping, *func*
  will be called for all values and a new dictionary is returned.
  """

  if isinstance(val, dict):
    result = {}
    for key, value in val.items():
      if isinstance(value, (dict, list)):
        value = _map_values(value, func)
      elif isinstance(value, str):
        value = func(value)
      if value is not Exclude:
        result[key] = value
  elif isinstance(val, list):
    result = []
    for item in val:
      if isinstance(item, (dict, list)):
        item = _map_values(item, func)
      elif isinstance(item, str):
        item = func(item)
      if item is not Exclude:
        result.append(item)
  else:
    raise TypeError(f'expected dict or list, got {type(val).__name__}')

  return result


class PartialTypeError(TypeError):
  """
  Raised when a partial expression does not result in a scalar value.
  """


class Environment:
  """
  Wrapper for a #jinja2.Environment for use in configuration rendering.
  """

  _SCALAR_TYPES = (str, int, float)

  def __init__(self,
    jinja_env_options: t.Optional[t.Mapping[str, t.Any]] = None,
    strict_undefined: bool = True,
    init_defaults: bool = True,
  ) -> None:

    self.jinja_env = jinja2.Environment(**(jinja_env_options or {}))
    self.variables: t.Dict[str, t.Any] = {}

    if strict_undefined:
      self.jinja_env.undefined = jinja2.StrictUndefined

    if init_defaults:
      self.init_defaults()

  def init_defaults(self) -> None:
    self.variables['exclude'] = Exclude
    self.add_filter('flatten', _filter_flatten)

  def add_filter(self, func: _JinjaFilter, name: t.Optional[str] = None) -> None:
    self.jinja_env.filters[name or func.__name__] = func

  def eval(self, expr: str, context: t.Mapping[str, t.Any]) -> t.Any:
    """
    Evaluate a single expression. If the entire expression is a partial (i.e. does not concatenate
    with a string at the beginning or end), the type yielded by the partial may be an arbitrary JSON
    serializable value. Otherwise, it must be a string and will raise a #PartialTypeError otherwise.

    ```yml
    {{ "foo" }}/bar             # Allowed
    {{ [1, 2] }}                # Allowed
    {{ [1, 2] }}/bar            # Not Allowed
    ```

    Important note: This method is NOT thread-safe.
    """

    # TODO(NiklasRosenstein): We're only checking the beginning and end of the expression, but
    #   it could just be encapsulated by two partials and still do string concatenation, as in
    #   `{{ a }}b{{ c }}`. The function will currently behave overly permissive and result in
    #   `a` and `b` to be rendered as strings, even if they are complex structures.

    expr = expr.strip()
    is_full_expr = expr.startswith(self.jinja_env.variable_start_string) and \
      expr.endswith(self.jinja_env.variable_end_string)

    result: t.Optional[t.Any] = None

    if is_full_expr:
      def _finalize(val: t.Any) -> str:
        nonlocal result
        result = val
        return ''
      self.jinja_env.finalize = _finalize
    else:
      def _finalize(val: t.Any) -> str:
        if not isinstance(val, self._SCALAR_TYPES):
          raise PartialTypeError('partial expression must yield scalar value, '
            f'got {type(val).__name__}')
        return val
      self.jinja_env.finalize = _finalize

    context = ChainDict(context or {}, self.variables)

    template = self.jinja_env.from_string(expr)
    render_result = template.render(context or {})

    if is_full_expr:
      return result
    else:
      return render_result

  def render(self, payload: _JsonType, context: t.Mapping[str, t.Any]) -> _JsonType:
    """
    Evaluates the given *payload*, rendering string valuse as Jinja2 templates.
    """

    # TODO(NiklasRosenstein): In order to access variables that in turn reference other
    #   variables, we would need to build a dependency graph and eval values in order.

    context = ChainDict(payload, context or {})
    func = functools.partial(self.eval, context=context)
    return _map_values(payload, func)


def merge_dicts(a: t.Dict, b: t.Dict, full_copy: bool = True) -> t.Dict:
  """
  Merges the values *a* and *b*. Dictionaries are merged on a key-by-key basis, whereas for
  lists *b* will be used in the place of *a* with any merging at all.
  """

  if not isinstance(a, dict):
    raise TypeError(f'a must be dict, got {type(a).__name__}')
  if not isinstance(b, dict):
    raise TypeError(f'b must be dict, got {type(b).__name__}')

  b = copy.deepcopy(b) if full_copy else b
  result = copy.deepcopy(a) if full_copy else a
  for key, value in b.items():
    if isinstance(value, dict) and key in result and isinstance(result[key], dict):
      value = merge_dicts(result[key], value, full_copy)
    result[key] = value

  return result


def load_yaml_files(files: t.List[str]) -> _JsonType:
  """
  Load multiple YAML files and merge them with *merge_dicts*.
  """

  result = {}
  for filename in files:
    with open(filename, 'r') as fp:
      result = merge_dicts(result, yaml.safe_load(fp))

  return result
