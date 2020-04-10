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

from nr.databind.rest import get_routes, MimeTypeMapper, Path, ParametrizedRoute, RequestWrapper, ServiceException, VoidRouteReturn
from nr.databind.core import ObjectMapper
from nr.databind.json import JsonModule
from nr.interface import Implementation
from typing import BinaryIO, Callable, Dict, List, Optional, TextIO

import flask
import logging

logger = logging.getLogger(__name__)


def get_default_mappers() -> Dict[str, ObjectMapper]:
  return {'application/json': ObjectMapper(JsonModule())}


class FlaskRequestWrapper(RequestWrapper):

  def __init__(self, path_parameters: Dict[str, str]):
    self.path_parameters = path_parameters

  def get_body(self) -> TextIO:
    if flask.request.stream:
      return flask.request.stream
    else:
      return

  def get_path_param(self, name: str) -> str:
    return self.path_parameters[name]

  def get_query_param(self, name: str) -> List[str]:
    return flask.request.args.getlist(name)

  def get_header(self, name: str) -> Optional[str]:
    return flask.request.headers.get(name)

  def get_file(self, name: str) -> BinaryIO:
    return flask.request.files[name]


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
    request = FlaskRequestWrapper(kwargs)

    try:
      result = self.route.invoke(self.mapper, self.impl, request)
    except ServiceException as exc:
      result = exc
    except Exception as exc:
      logger.exception('An unhandled exception ocurred.')
      result = ServiceException('An unhandled exception ocurred.')
      if self.debug:
        result.parameters['debug:stackTrace'] = traceback.format_exc()

    if isinstance(result, ServiceException):
      status_code = result.http_status_code
      result = self.mapper.se(content_type, result, ServiceException)
    elif isinstance(self.route.return_, VoidRouteReturn):
      if result is not None:
        logger.warning('discarding return value of %s', self)
      status_code = 201
      result = ''
    else:
      status_code = 200

    response = flask.make_response(result, status_code)
    response.headers['Content-type'] = content_type
    return response


def bind_resource(app: flask.Flask, prefix: str, resource: Implementation):
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
  mapper = MimeTypeMapper.default()
  for route in routes:
    path = (prefix + route.route.http.path).sub(_sub_param)
    impl = getattr(resource, route.name)
    logger.debug('Binding route %r to Flask application %r at %r',
      route.fqn, app.name, str(path))
    view = FlaskRouteWrapper(mapper, route, impl)
    app.add_url_rule(str(path), route.fqn, view, methods=[route.route.http.method])
