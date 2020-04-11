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

from nr.databind.rest import (
  PATH_PARAMETER_CONTENT_TYPE,
  get_routes,
  MimeTypeMapper,
  Path,
  ParametrizedRoute,
  RouteParam,
  RouteReturn,
  ParamVisitor,
  ServiceException,
  BadRequest,
)
from nr.databind.core import CollectionType, ObjectMapper, translate_type_def
from nr.databind.json import JsonModule
from nr.interface import Implementation
from nr.pylang.utils import NotSet
from typing import Any, BinaryIO, Callable, Dict, List, Optional, TextIO

import flask
import logging

logger = logging.getLogger(__name__)


def get_default_mappers() -> Dict[str, ObjectMapper]:
  return {'application/json': ObjectMapper(JsonModule())}


class FlaskParamVisitor(ParamVisitor):

  def __init__(self, mapper: MimeTypeMapper, path_parameters: Dict[str, str]) -> None:
    self.mapper = mapper
    self.path_parameters = path_parameters

  def visit_Path(self, param: RouteParam.Path) -> Any:
    value: str = self.path_parameters[param.name]
    return self.mapper.dd(PATH_PARAMETER_CONTENT_TYPE, value, param.type_annotation)

  def visit_Body(self, param: RouteParam.Body) -> Any:
    if flask.request.stream:
      fp = flask.request.stream
    else:
      raise NotImplementedError('not sure how to implement this yet')
    return self.mapper.dd(param.content_type, fp, param.type_annotation)

  def visit_Header(self, param: RouteParam.Header) -> Any:
    value: Optional[str] = flask.request.headers.get(param.name)
    if value is None:
      if param.default is not NotSet:
        return param.default
      raise BadRequest('missing required header', parameters={'header': param.name})
    return self.mapper.dd(PATH_PARAMETER_CONTENT_TYPE, value, param.type_annotation)

  def visit_Query(self, param: RouteParam.Query) -> Any:
    value: List[str] = flask.request.args.getlist(param.name)
    if not value:
      if param.default is not NotSet:
        return param.default
      raise BadRequest('missing required query parameter', parameters={'queryParam': param.name})
    type_def = translate_type_def(param.type_annotation)
    if not isinstance(type_def, CollectionType):
      value = value[0]
    return self.mapper.dd(PATH_PARAMETER_CONTENT_TYPE, value, type_def)

  def visit_File(self, param: RouteParam.File) -> Any:
    return flask.request.files[name]

  def visit_Custom(self, param: RouteParam.Custom) -> Any:
    return param.read(self)


class FlaskRouteWrapper:

  def __init__(self, mapper: MimeTypeMapper, route: ParametrizedRoute, impl: Callable, debug: bool = False):
    self.mapper = mapper
    self.route = route
    self.impl = impl
    self.debug = debug

  def __call__(self, **kwargs):
    """
    This is called from Flask when a request matches this route. Here we
    retrieve the path parameters as well as any other parameters from
    #flask.request and pass them to the implementation.
    """

    # Handle path parameters.
    for key, value in kwargs.items():
      if key not in self.route.parameters:
        raise RuntimeError('unexpected path parameter for Flask route {!r}')

    content_type = self.route.route.content_type
    visitor = FlaskParamVisitor(self.mapper, kwargs)

    try:
      kwargs = self.route.build_parameters(visitor)
      result = self.impl(**kwargs)
    except Exception as exc:
      if not isinstance(exc, ServiceException):
        logger.exception('An unhandled exception ocurred.')
        exc = ServiceException('An unhandled exception ocurred.')
      result = exc
      if self.debug:
        result.parameters['debug:stackTrace'] = traceback.format_exc()

    if isinstance(result, ServiceException):
      status_code = result.http_status_code
      result = self.mapper.se(content_type, result, ServiceException)
    elif self.route.return_.is_void():
      if result is not None:
        logger.warning('discarding return value of %s', self)
      status_code = 201
      result = ''
    elif self.route.return_.is_passthrough():
      return result
    elif self.route.return_.is_mapped():
      status_code = 200
      result = self.mapper.se(content_type, result, self.route.return_.type_annotation)
    else:
      raise RuntimeError('unknown return type: {!r}'.format(self.route.return_))

    response = flask.make_response(result, status_code)
    response.headers['Content-type'] = content_type
    return response


def bind_resource(
    app: flask.Flask,
    prefix: str,
    resource: Implementation,
    mapper: MimeTypeMapper = None):
  """
  Bind a resource to a flask application under the specified prefix. The
  prefix may be an empty string.
  """

  if not isinstance(resource, Implementation):
    raise TypeError('expected Implementation object, got "{}"'
      .format(type(resource).__name__))

  routes: List[ParametrizedRoute] = []
  for interface in type(resource).__implements__:
    routes += get_routes(interface)

  if not routes:
    raise ValueError('interfaces implemented by "{}" provide no routes'
      .format(type(resource).__name__))

  def _sub_param(x):
    if x['type'] == 'parameter':
      return {'type': 'text', 'text': '<' + x['parameter'] + '>'}
    return x

  prefix = Path(prefix)
  mapper = mapper or MimeTypeMapper.default()
  for route in routes:
    path = (prefix + route.route.http.path).sub(_sub_param)
    impl = getattr(resource, route.name)
    logger.debug('Binding route %r to Flask application %r at %r',
      route.fqn, app.name, str(path))
    view = FlaskRouteWrapper(mapper, route, impl)
    app.add_url_rule(str(path), route.fqn, view, methods=[route.route.http.method])
