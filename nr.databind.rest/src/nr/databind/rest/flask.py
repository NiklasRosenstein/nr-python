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
  RouteResult,
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
import traceback

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
      raise BadRequest('missing required header', header=param.name)
    return self.mapper.dd(PATH_PARAMETER_CONTENT_TYPE, value, param.type_annotation)

  def visit_Query(self, param: RouteParam.Query) -> Any:
    value: List[str] = flask.request.args.getlist(param.name)
    if not value:
      if param.default is not NotSet:
        return param.default
      raise BadRequest('missing required query parameter', queryParam=param.name)
    type_def = translate_type_def(param.type_annotation)
    if not isinstance(type_def, CollectionType):
      value = value[0]
    return self.mapper.dd(PATH_PARAMETER_CONTENT_TYPE, value, type_def)

  def visit_File(self, param: RouteParam.File) -> Any:
    return flask.request.files[param.name]

  def visit_Custom(self, param: RouteParam.Custom) -> Any:
    return param.read(self)


class FlaskRouteWrapper:

  def __init__(
      self,
      mapper: MimeTypeMapper,
      route: ParametrizedRoute,
      impl: Callable,
      debug: bool = False
      ) -> None:
    self.mapper = mapper
    self.route = route
    self.impl = impl
    self.debug = debug

  def __repr__(self):
    return 'FlaskRouteWrapper(route.name={!r})'.format(self.route.name)

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

    def _handle_request():
      kwargs = self.route.build_parameters(visitor)
      result = self.impl(**kwargs)

      if isinstance(result, RouteResult):
        return_type, result = result.type, result.value
      else:
        return_type = self.route.return_

      if return_type.is_void():
        if result is not None:
          logger.warning('discarding return value of %s', self)
        return '', 201
      elif return_type.is_passthrough():
        return result, None
      elif return_type.is_mapped():
        result = self.mapper.se(content_type, result, return_type.type_annotation)
        return result, 200
      else:
        raise RuntimeError('unknown return type: {!r}'.format(return_type))

    try:
      result, status_code = _handle_request()
    except Exception as exc:
      if not isinstance(exc, ServiceException):
        exc = ServiceException('An unhandled exception ocurred.')
        logger.exception('An unhandled exception ocurred in %s (uuid: %s).', self, exc.uuid)
        if self.debug:
          exc.parameters['traceback'] = traceback.format_exc()
      else:
        logger.info('%s', traceback.format_exc())
      status_code = exc.http_status_code
      result = self.mapper.se(content_type, exc, ServiceException)

    if status_code is None:
      return result  # Passthrough

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
  mapper = mapper or MimeTypeMapper.json()
  for route in routes:
    path = str((prefix + route.route.http.path).sub(_sub_param)).rstrip('/')
    impl = getattr(resource, route.name)
    logger.debug('Binding route %r to Flask application %r at %r',
      route.fqn, app.name, str(path))
    view = FlaskRouteWrapper(mapper, route, impl, debug=True)
    app.add_url_rule(str(path), route.fqn, view, methods=[route.route.http.method])
