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

import abc
import collections
import copy
import importlib
import inspect
import json
import io
import re
import uuid

from nr.collections.abc import Mapping
from nr.collections.generic import Generic
from nr.databind.core import ObjectMapper, Field, FieldName, Struct, OptionalType
from nr.databind.json import JsonModule, JsonSerializer
from nr.interface import Interface, Method as _InterfaceMethod
from nr.metaclass.deconflict import deconflicted_base
from nr.pylang.utils import classdef, NotSet
from nr.sumtype import Constructor, Sumtype, add_constructor_tests
from typing import Any, BinaryIO, Callable, Dict, List, Optional, TextIO, Type, TypeVar, Union

__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
__version__ = '0.0.3'

JSON_CONTENT_TYPE = 'application/json'
PATH_PARAMETER_CONTENT_TYPE = 'x-path-param'

#: Can be used in a return annotation of a route to denote that this
#: route returns a value that should be passed through to the framework.
Response = TypeVar('Response')


# (De-) serializable exceptions that can be thrown by services that will
# propagate to the client.

@JsonSerializer(serialize='_serialize', deserialize='_deserialize')
class ServiceException(Exception):
  " Generic exception type. "

  http_status_code = 500

  def __init__(self, message: Optional[str], parameters: dict = None) -> None:
    self.message = message
    self.parameters = parameters or {}
    self.uuid = str(uuid.uuid4())

  def __str__(self):
    result = ['(uuid: {}) {}'.format(self.uuid, self.message)]
    filtered = {k: v for k, v in self.parameters.items() if k != 'traceback'}
    if filtered:
      result.append(json.dumps(filtered, indent=2))
    if 'traceback' in self.parameters:
      result.append('\nOriginal traceback:')
      for line in self.parameters['traceback'].splitlines():
        result.append(' | ' + line)
    return '\n'.join(result)

  @staticmethod
  def _serialize(mapper, node):
    fqn =  type(node.value).__module__ + ':' + type(node.value).__name__
    result = {'errorType': fqn, 'errorUuid': node.value.uuid}
    if node.value.message:
      result['errorMessage'] = node.value.message
    if node.value.parameters:
      result['errorParameters'] = node.value.parameters
    return result

  @staticmethod
  def _deserialize(mapper, node):
    if not isinstance(node.value, Mapping):
      raise node.type_error()
    if 'errorType' not in node.value:
      raise node.value_error('missing "errorType" key')
    fqn = node.value['errorType']
    module, member = fqn.split(':')
    exception_cls = getattr(importlib.import_module(module), member)
    exc = exception_cls.__new__(exception_cls)
    exc.message = node.value.get('errorMessage')
    exc.parameters = node.value.get('errorParameters', {})
    exc.uuid = node.value['errorUuid']
    return exc


class NotFound(ServiceException):
  http_status_code = 404

  def __init__(self, message: str = None, **kwargs):
    super().__init__(message, kwargs)


class BadRequest(ServiceException):
  http_status_code = 400

  def __init__(self, message: str = None, **kwargs):
    super().__init__(message, kwargs)


class InvalidArgument(BadRequest):
  pass


# Route data and decoration

@add_constructor_tests
class RouteParam(Sumtype):
  class _AnnotatedParam(Struct):
    type_annotation = Field(Any)

  @Constructor
  class Path(_AnnotatedParam):
    name = Field(str, default=None)

  @Constructor
  class Body(_AnnotatedParam):
    content_type = Field(str, default=None)

  @Constructor
  class Query(_AnnotatedParam):
    name = Field(str, default=None)
    default = Field(Any, default=lambda: NotSet)

  @Constructor
  class Header(_AnnotatedParam):
    name = Field(str, default=None)
    default = Field(Any, default=lambda: NotSet)

  @Constructor
  class File(Struct):
    name = Field(str, default=None)

  @Constructor
  class Custom(Struct):
    """
    Can be used to implement custom route parameters that are tied to a
    specific framework and they cannot be properly supported in the client
    generation without custom code additions.
    """

    read = Field(Any)  # type: Callable[[Any], Any]


@add_constructor_tests
class RouteReturn(Sumtype):
  Void = Constructor()
  Passthrough = Constructor()
  Mapped = Constructor('type_annotation,content_type')


class RouteResult:

  def __init__(self, type_: RouteReturn, value: Any) -> None:
    self.type = type_
    self.value = value


class Path:
  """
  Represents a parametrized path. Parameters are defined by enclosing them
  in curly braces.

  >>> path = Path("/my-endpoint/{myParameter}")
  >>> path.parameters
  ['myParameter']
  """

  classdef.comparable(['components'])

  def __init__(self, path):
    self.components = []
    self.parameters = []
    offset = 0
    for match in re.finditer(r'\{([\w\d]+)\}', path):
      if offset < match.start():
        self.components.append({'type': 'text', 'text': path[offset:match.start()]})
      parameter = match.group(1)
      if parameter in self.parameters:
        raise ValueError('duplicate parameter in path string: {!r}'.format(
          parameter))
      self.components.append({'type': 'parameter', 'parameter': parameter})
      self.parameters.append(parameter)
      offset = match.end()
    if offset < len(path):
      self.components.append({'type': 'text', 'text': path[offset:]})

  def __str__(self):
    parts = []
    for component in self.components:
      if component['type'] == 'text':
        parts.append(component['text'])
      else:
        parts.append('{' + component['parameter'] + '}')
    return ''.join(parts)

  def __repr__(self):
    return 'Path({!r})'.format(str(self))

  def __add__(self, other: 'Path') -> 'Path':
    self = copy.copy(self)
    self.components = self.components + other.components
    self.parameters = self.parameters + other.parameters
    return self

  def sub(self, map_function):
    self = copy.copy(self)
    self.components = list(map(map_function, self.components))
    self.parameters = [x['parameter'] for x in self.components if x['type'] == 'parameter']
    return self

  def render(self, parameters: Dict[str, str]) -> str:
    def func(x):
      if x['type'] == 'parameter':
        return {'type': 'text', 'text': parameters[x['parameter']]}
      return x
    return str(self.sub(func))


class HttpData:
  """
  Represents HTTP route parameters consisting of a method and the path.
  """

  classdef.comparable(['method', 'path'])

  _METHODS = ['GET', 'HEAD', 'POST', 'POST', 'PUT', 'DELETE', 'CONNECT',
              'OPTIONS', 'TRACE', 'PATCH']
  _PARSE_REGEX = re.compile(r'({})\s+(/.*)'.format('|'.join(_METHODS)))

  @classmethod
  def parse(cls, s: str):
    assert isinstance(s, str), type(s)
    match = cls._PARSE_REGEX.match(s)
    if not match:
      raise ValueError('invalid http specifier: {!r}'.format(s))
    return cls(match.group(1), Path(match.group(2)))

  def __init__(self, method, path):
    self.method = method
    self.path = path

  def __str__(self):
    return '{} {}'.format(self.method, self.path)

  def __repr__(self):
    return 'HttpData(method={!r}, path={!r})'.format(self.method, self.path)


class RouteData:
  """
  Route data that is attached to a function with the #Route decorator.
  """

  classdef.comparable(['http', 'content_type'])
  classdef.repr(['http', 'content_type'])

  def __init__(self, http: HttpData, content_type: str):
    self.http = http
    self.content_type = content_type


class ParametrizedRoute:
  """
  A route that contains the resolved parameter information and a reference
  to the interface where the route is defined. This is returned from the
  #get_routes() function.
  """

  classdef.comparable(['name', 'signature', 'route', 'interface', 'parameters', 'return_'])
  classdef.repr(['name', 'signature', 'route', 'interface', 'parameters', 'return_'])

  def __init__(
      self,
      name: str,
      signature: inspect.Signature,
      route: RouteData,
      interface: Type[Interface],
      parameters: Dict[str, 'RouteParam'],
      return_: 'RouteReturn'
      ) -> None:
    self.name = name
    self.signature = signature
    self.route = route
    self.interface = interface
    self.parameters = parameters
    self.return_ = return_

  @property
  def fqn(self) -> str:
    return self.interface.__module__ + '.' + self.interface.__name__ + ':' + self.name

  @classmethod
  def from_function(
      cls,
      route: RouteData,
      interface: Type[Interface],
      func: Callable,
      ) -> 'ParametrizedRoute':
    """
    Creates a #ParametrizedRoute from a function and the #RouteData that was
    associated with that function. This will generate the *parameters* for
    the #ParametrizedRoute constructor.
    """

    sig = inspect.signature(func)

    # Determine the return-type of the route from the annotation.
    if sig.return_annotation in (inspect._empty, None):
      return_ = RouteReturn.Void()
    elif sig.return_annotation is Response:
      return_ = RouteReturn.Passthrough()
    else:
      return_ = RouteReturn.Mapped(sig.return_annotation, route.content_type)

    parameters = {}

    # Route path parameters.
    for parameter in route.http.path.parameters:
      if parameter not in sig.parameters:
        raise TypeError('function "{}.{}" does not provide parameter {}'
          .format(interface.__name__, func.__name__, parameter))
      annotation = sig.parameters[parameter].annotation
      if annotation is inspect._empty:
        annotation = NotSet
      parameters[parameter] = RouteParam.Path(annotation, parameter)

    # Other parameter types.
    for parameter in sig.parameters.values():
      if parameter.name in parameters or parameter.name == 'self':
        continue
      if isinstance(parameter.annotation, RouteParam):
        if getattr(parameter.annotation, 'name', '???') is None:
          parameter.annotation.name = parameter.name
        parameters[parameter.name] = parameter.annotation
      elif isinstance(parameter.annotation, type) and \
          issubclass(parameter.annotation, RouteParam):
        parameters[parameter.name] = parameter.annotation()
      else:
        parameters[parameter.name] = RouteParam.Body(parameter.annotation)

      # Fill in name/default/content_type.
      param = parameters[parameter.name]
      if hasattr(param, 'name') and not param.name:
        param.name = parameter.name
      if hasattr(param, 'default') and parameter.default is not inspect._empty:
        if parameter.default is None and not isinstance(param.type_annotation, OptionalType):
          param.type_annotation = OptionalType(param.type_annotation)
        param.default = parameter.default
      if hasattr(param, 'content_type') and not param.content_type:
        param.content_type = route.content_type

    body_params = list(k for k, v in
      parameters.items() if isinstance(v, RouteParam.Body))
    if len(body_params) > 1:
      raise TypeError('found multiple unmatched parameters that could serve '
        'as candiates for the request body, but there can be only one or no '
        'body parameter, candidates are: {!r}'.format(body_params))

    return cls(func.__name__, sig, route, interface, parameters, return_)

  def build_parameters(self, visitor: 'ParameterVisitor') -> Dict[str, Any]:
    kwargs = {}
    for name, param in self.parameters.items():
      kwargs[name] = visitor.dispatch(param)
    return kwargs


def Route(http: str, content_type: str = JSON_CONTENT_TYPE):
  """
  This is a decorator for functions on an interface to specify the HTTP
  method and path (including path parameters).
  """

  data = RouteData(HttpData.parse(http), content_type)

  def decorator(func):
    args = inspect.signature(func)
    for param in data.http.path.parameters:
      if param not in args.parameters:
        raise ValueError('missing parameter {!r} in function "{}"'.format(
          param, func.__name__))
    func.__route__ = data
    return func

  return decorator


def get_routes(interface: Type[Interface]) -> List[ParametrizedRoute]:
  """
  Retrieves the routes from an interface.
  """

  if not issubclass(interface, Interface):
    raise TypeError('expected Interface subclass, got {}'
      .format(interface.__name__))

  routes = []
  for member in interface.members():
    if isinstance(member, _InterfaceMethod):
      route_data = getattr(member.original, '__route__', None)
      if route_data is not None:
        assert isinstance(route_data, RouteData)
        routes.append(ParametrizedRoute.from_function(
          route_data, interface, member.original))
  return routes


# Content Encoders

class ContentEncoder(metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def encode(self, value: Any, out: TextIO):
    ...

  @abc.abstractmethod
  def decode(self, fp: TextIO) -> Any:
    ...


class JsonContentEncoder(ContentEncoder):

  def __init__(self, for_path_parameters: bool = False) -> None:
    self.for_path_parameters = for_path_parameters

  def encode(self, value: Any, out: TextIO):
    if self.for_path_parameters and isinstance(value, str):
      out.write(value)
    else:
      json.dump(value, out)

  def decode(self, fp: TextIO) -> Any:
    if self.for_path_parameters:
      content = fp.read()
      try:
        return json.loads(content)
      except json.JSONDecodeError:
        return content
    else:
      return json.load(fp)


class MimeTypeMapper:

  def __init__(self):
    self._types = {}
    self.register(
      PATH_PARAMETER_CONTENT_TYPE,
      JsonContentEncoder(for_path_parameters=True),
      ObjectMapper(JsonModule()))

  def __getitem__(self, content_type: str) -> dict:
    try:
      return self._types[content_type]
    except KeyError:
      raise KeyError('no handler for content type {!r} found'.format(content_type))

  def register(self, mime_type: str, encoder: ContentEncoder, mapper: ObjectMapper):
    self._types[mime_type] = {'encoder': encoder, 'mapper': mapper}

  def encode(self, mime_type: str, value: Any, out: TextIO):
    self[mime_type]['encoder'].encode(value, out)

  def decode(self, mime_type: str, fp: TextIO) -> Any:
    return self[mime_type]['encoder'].decode(fp)

  def serialize(
      self,
      mime_type: str,
      value: Any,
      type_def: Any,
      filename: str = None
      ) -> Any:
    return self[mime_type]['mapper'].serialize(
      value, type_def, filename=filename)

  def deserialize(
      self,
      mime_type: str,
      value: Any,
      type_def: Any,
      filename: str = None
      ) -> Any:
    return self[mime_type]['mapper'].deserialize(
      value, type_def, filename=filename)

  def se(
      self,
      mime_type: str,
      value: Any,
      type_def: Any,
      out: TextIO = None,
      filename: str = None
      ) -> Optional[str]:
    value = self.serialize(mime_type, value, type_def, filename=filename)
    output = out or io.StringIO()
    self.encode(mime_type, value, output)
    return output.getvalue() if out is None else None

  def dd(
      self,
      mime_type: str,
      in_value: Union[TextIO, str],
      type_def: Any,
      filename: str = None
      ) -> Any:
    if isinstance(in_value, str):
      in_value = io.StringIO(in_value)
    in_value = self.decode(mime_type, in_value)
    return self.deserialize(mime_type, in_value, type_def, filename=filename)

  @classmethod
  def json(cls, mapper: ObjectMapper = None):
    mime_mapper = cls()
    mime_mapper.register(
      'application/json',
      JsonContentEncoder(),
      mapper or ObjectMapper(JsonModule()))
    return mime_mapper


# Helpers

class ParamVisitor:

  def dispatch(self, param: RouteParam):
    method_name = 'visit_' + type(param).__name__.rpartition('.')[2]
    return getattr(self, method_name)(param)


class Page(deconflicted_base(Struct, Generic)):
  """
  Template that represents a paginated type for a specific item type. Can
  be instantiated with the #of() method.
  """

  items = Field([Any])
  next_page_token = Field(Any, FieldName('nextPageToken'), nullable=True)

  def __generic_init__(self, item_type: Any, token_type: Any = int):
    self.items = Field([item_type])
    self.next_page_token = Field(token_type, FieldName('nextPageToken'), nullable=True)
