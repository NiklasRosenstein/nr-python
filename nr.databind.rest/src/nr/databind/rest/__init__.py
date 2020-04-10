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
import inspect
import json
import io
import re

from nr.databind.core import CollectionType, ObjectMapper, translate_type_def
from nr.databind.json import JsonModule, JsonSerializer
from nr.interface import Interface, Method as _InterfaceMethod
from nr.pylang.utils import classdef, NotSet
from typing import Any, BinaryIO, Callable, Dict, List, Optional, TextIO, Type, TypeVar, Union

__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
__version__ = '0.0.1'

DEFAULT_CONTENT_TYPE = 'application/json'

#: Can be used in a return annotation of a route to denote that this
#: route returns a value that should be passed through to the framework.
Response = TypeVar('Response')


# Route data and decoration

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
    if offset < len(path) - 1:
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

  classdef.comparable(['name', 'route', 'interface', 'parameters', 'return_'])
  classdef.repr(['name', 'route', 'interface', 'parameters', 'return_'])

  def __init__(
      self,
      name: str,
      route: RouteData,
      interface: Type[Interface],
      parameters: Dict[str, 'RouteParameter'],
      return_: 'RouteReturn'
      ) -> None:
    self.name = name
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
      return_ = VoidRouteReturn()
    elif sig.return_annotation is Response:
      return_ = PassthroughRouteReturn()
    else:
      return_ = MappedRouteReturn(sig.return_annotation, route.content_type)

    parameters = {}

    # Route path parameters.
    for parameter in route.http.path.parameters:
      if parameter not in sig.parameters:
        raise TypeError('function "{}.{}" does not provide parameter {}'
          .format(interface.__name__, func.__name__, parameter))
      annotation = sig.parameters[parameter].annotation
      if annotation is inspect._empty:
        annotation = NotSet
      parameters[parameter] = PathParameter(annotation, parameter)

    # Other parameter types.
    for parameter in sig.parameters.values():
      if parameter.name in parameters or parameter.name == 'self':
        continue
      if isinstance(parameter.annotation, RouteParameter):
        if getattr(parameter.annotation, 'name', '???') is None:
          parameter.annotation.name = parameter.name
        parameters[parameter.name] = parameter.annotation
      elif isinstance(parameter.annotation, type) and \
          issubclass(parameter.annotation, RouteParameter):
        raise TypeError('RouteParameter implementation must be instantiated '
          'in route annotations, found type object instead in "{}.{}" named '
          '{}.'.format(interface.__name__, func.__name__, parameter.name))
      else:
        parameters[parameter.name] = BodyParameter(parameter.annotation)
      # Fill in the default value.
      param = parameters[parameter.name]
      if hasattr(param, 'default') and parameter.default is not inspect._empty:
        param.default = parameter.default

    body_params = list(k for k, v in
      parameters.items() if isinstance(v, BodyParameter))
    if len(body_params) > 1:
      raise TypeError('found multiple unmatched parameters that could serve '
        'as candiates for the request body, but there can be only one or no '
        'body parameter, candidates are: {!r}'.format(body_params))

    return cls(func.__name__, route, interface, parameters, return_)

  def invoke(self, mapper: 'MimeTypeMapper', impl: Callable, request: 'RequestWrapper') -> Any:
    kwargs = {}
    for name, param in self.parameters.items():
      kwargs[name] = param.read(mapper, request)
    result = impl(**kwargs)
    return self.return_.wrap(mapper, result)


def Route(http: str, content_type: str = DEFAULT_CONTENT_TYPE):
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


class ContentEncoder(metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def encode(self, value: Any, out: TextIO):
    ...

  @abc.abstractmethod
  def decode(self, fp: TextIO) -> Any:
    ...


class JsonContentEncoder(ContentEncoder):

  def __init__(self, try_or_else_string: bool = False) -> None:
    self.try_or_else_string = try_or_else_string

  def encode(self, value: Any, out: TextIO):
    json.dump(value, out)

  def decode(self, fp: TextIO) -> Any:
    if self.try_or_else_string:
      content = fp.read()
      try:
        return json.loads(content)
      except json.JSONDecodeError:
        return content
    else:
      return json.load(fp)


class PlainContentEncoder(ContentEncoder):

  def encode(self, value: Any, out: TextIO) -> str:
    assert isinstance(value, str), type(value)
    out.write(value)

  def decode(self, fp: TextIO) -> Any:
    return fp.read()


class MimeTypeMapper:

  def __init__(self):
    self._types = {}

  def register(self, mime_type: str, encoder: ContentEncoder, mapper: ObjectMapper):
    self._types[mime_type] = {'encoder': encoder, 'mapper': mapper}

  def encode(self, mime_type: str, value: Any, out: TextIO):
    self._types[mime_type]['encoder'].encode(value, out)

  def decode(self, mime_type: str, fp: TextIO) -> Any:
    return self._types[mime_type]['encoder'].decode(fp)

  def serialize(self, mime_type: str, value: Any, type_def: Any) -> Any:
    return self._types[mime_type]['mapper'].serialize(value, type_def)

  def deserialize(self, mime_type: str, value: Any, type_def: Any) -> Any:
    return self._types[mime_type]['mapper'].deserialize(value, type_def)

  def se(self, mime_type: str, value: Any, type_def: Any, out: TextIO = None) -> Optional[str]:
    value = self.serialize(mime_type, value, type_def)
    output = out or io.StringIO()
    self.encode(mime_type, value, output)
    return output.getvalue() if out is None else None

  def dd(self, mime_type: str, in_value: Union[TextIO, str], type_def: Any) -> Any:
    if isinstance(in_value, str):
      in_value = io.StringIO(in_value)
    in_value = self.decode(mime_type, in_value)
    return self.deserialize(mime_type, in_value, type_def)

  @classmethod
  def default(cls):
    mime_mapper = cls()
    mime_mapper.register(
      'application/json',
      JsonContentEncoder(),
      ObjectMapper(JsonModule()))
    mime_mapper.register(
      PathParameter.CONTENT_TYPE,
      JsonContentEncoder(try_or_else_string=True),
      ObjectMapper(JsonModule()))
    return mime_mapper


class RequestWrapper(metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def get_body(self) -> TextIO:
    ...

  @abc.abstractmethod
  def get_path_param(self, name: str) -> str:
    ...

  @abc.abstractmethod
  def get_query_param(self, name: str) -> List[str]:
    ...

  @abc.abstractmethod
  def get_header(self, name: str) -> Optional[str]:
    ...

  @abc.abstractmethod
  def get_file(self, name: str) -> BinaryIO:
    ...


# Route parametrization types

class RouteParameter(metaclass=abc.ABCMeta):
  """ Represents a parameter to a route. """

  @abc.abstractmethod
  def read(self, mapper: MimeTypeMapper, request: RequestWrapper) -> Any:
    ...


class PathParameter(RouteParameter):

  classdef.comparable(['type_annotation', 'name'])
  classdef.repr(['type_annotation', 'name'])
  CONTENT_TYPE = 'x-path-parameter'

  def __init__(self, type_annotation: Any, name: str) -> None:
    self.name = name
    self.type_annotation = type_annotation

  def read(self, mapper: MimeTypeMapper, request: RequestWrapper) -> Any:
    value: str = request.get_path_param(self.name)
    return mapper.dd(self.CONTENT_TYPE, value, self.type_annotation)


class BodyParameter(RouteParameter):

  classdef.comparable(['type_annotation', 'content_type'])
  classdef.repr(['type_annotation', 'content_type'])

  def __init__(
      self,
      type_annotation: Any,
      content_type: str = DEFAULT_CONTENT_TYPE
      ) -> None:
    self.type_annotation = type_annotation
    self.content_type = content_type

  def read(self, mapper: MimeTypeMapper, request: RequestWrapper) -> Any:
    body_fp: TextIO = request.get_body()
    return mapper.dd(self.content_type, body_fp, self.type_annotation)


class HeaderParameter(RouteParameter):

  classdef.comparable(['type_annotation', 'name', 'default'])
  classdef.repr(['type_annotation', 'name', 'default'])

  def __init__(self, type_annotation: Any, name: str = None, default: Any = NotSet) -> None:
    self.type_annotation = type_annotation
    self.name = name
    self.default = default

  def read(self, mapper: MimeTypeMapper, request: RequestWrapper) -> Any:
    value: Optional[str] = request.get_header(self.name)
    if value is None:
      if self.default is not NotSet:
        return self.default
      # TODO (@NiklasRosenstein): Raise some exception that can be interpreted
      #   as a Bad Request somewhere up in the stacktrace.
      raise RuntimeError('missing query parameter {!r}'.format(self.name))
    return mapper.dd(PathParameter.CONTENT_TYPE, value, self.type_annotation)


class QueryParameter(RouteParameter):

  classdef.comparable(['type_annotation', 'name', 'default'])
  classdef.repr(['type_annotation', 'name', 'default'])

  def __init__(self, type_annotation: Any, name: str = None, default: Any = NotSet) -> None:
    self.type_annotation = type_annotation
    self.name = name
    self.default = default

  def read(self, mapper: MimeTypeMapper, request: RequestWrapper) -> Any:
    value: List[str] = request.get_query_param(self.name)
    if not value:
      if self.default is not NotSet:
        return self.default
      raise BadRequest('missing required query parameter', parameters={'parameterName': self.name})
    type_def = translate_type_def(self.type_annotation)
    if not isinstance(type_def, CollectionType):
      value = value[0]
    return mapper.dd(PathParameter.CONTENT_TYPE, value, type_def)


class FileParameter(RouteParameter):

  def __init__(self, name: str = None) -> None:
    self.name = name

  def read(self, mapper: MimeTypeMapper, request: RequestWrapper) -> Any:
    return request.get_file(self.name)


class RouteReturn(metaclass=abc.ABCMeta):
  """ Base class that describes the return type of a route. """

  @abc.abstractmethod
  def wrap(self, mapper: MimeTypeMapper, return_value: Any) -> Any:
    ...


class VoidRouteReturn(RouteReturn):
  """ Represents a VOID response (eg. 201 No Content). """

  classdef.comparable([])
  classdef.repr([])

  def wrap(self, mapper: MimeTypeMapper, return_value: Any) -> Any:
    return return_value


class PassthroughRouteReturn(RouteReturn):
  """
  Represents that the return value of the route implementation should be
  passed through to the framework. The implementation would usually return
  some value that is natively accepted by the framework (eg. a response
  object).
  """

  classdef.comparable([])
  classdef.repr([])

  def wrap(self, mapper: MimeTypeMapper, return_value: Any) -> Any:
    return framework.return_passthrough(return_value)


class MappedRouteReturn(RouteReturn):
  """
  Represents that the return value should be mapped to a serializable form
  using the frameworks object serializers. The object mapper is picked
  depending on the specified *content_type*.
  """

  classdef.comparable(['type_annotation', 'content_type'])
  classdef.repr(['type_annotation', 'content_type'])

  def __init__(
      self,
      type_annotation: Any,
      content_type: str = DEFAULT_CONTENT_TYPE
      ) -> None:
    self.type_annotation = type_annotation
    self.content_type = content_type

  def wrap(self, mapper: MimeTypeMapper, return_value: Any) -> Any:
    return mapper.se(self.content_type, return_value, self.type_annotation)


# Exception types


def _json_serialize_service_exception(mapper, node):
  result = {'errorCode': node.value.error_code}
  if node.value.message:
    result['message'] = node.value.message
  if node.value.parameters:
    result['parameters'] = node.value.parameters
  return result


@JsonSerializer(serialize=_json_serialize_service_exception)
class ServiceException(Exception):
  " Generic exception type. "

  error_code = 'INTERNAL'
  http_status_code = 500

  def __init__(self, message: str, parameters: dict = None) -> None:
    self.message = message
    self.parameters = parameters or {}

  def __str__(self):
    return '{} ({})'.format(self.message, self.parameters)


class BadRequest(ServiceException):

  error_code = 'BadRequest'
  http_status_code = 400


class InvalidArgument(BadRequest):

  error_code = 'InvalidArgument'
