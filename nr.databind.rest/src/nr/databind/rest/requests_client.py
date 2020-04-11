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

from . import (
  PATH_PARAMETER_CONTENT_TYPE,
  get_routes,
  ParametrizedRoute,
  RouteParam,
  MimeTypeMapper
)
from nr.collections.generic import Generic
from nr.interface import Interface, implements
from nr.pylang.utils import NotSet

import functools
import requests


class ResourceClient(Generic):
  """
  A template class for resource clients.
  """

  def __generic_new__(metacls, name, bases, attrs):
    self = super().__generic_new__(metacls, name, bases, attrs)
    return implements(self._resource)(self)

  def __generic_init__(cls, resource: Interface):
    cls._resource = resource

    def bind(func, route):
      @functools.wraps(func)
      def wrapper(self, *args, **kwargs):
        return func(self, route, *args, **kwargs)
      return wrapper

    methods = {}
    for route in get_routes(resource):
      dispatcher = bind(cls.__route_dispatcher, route)
      setattr(cls, route.name, dispatcher)

  def __init__(self, base_url: str, mapper: MimeTypeMapper, session: requests.Session):
    assert not self.__is_generic__, 'cannot instantiate generic ResourceClient'
    self._base_url = base_url
    self._mapper = mapper
    self._session = session

  @staticmethod
  def __route_dispatcher(self, __route: ParametrizedRoute, **kwargs):
    path_parameters = {}
    headers = {}
    params = {}
    body = None
    files = {}

    def _get(param: RouteParam):
      try:
        return kwargs[param.name]
      except KeyError:
        if param.default is not NotSet:
          return param.default
        raise TypeError('{}() missing keyword argument "{}"'.format(
          __route.name, name))

    for param in __route.parameters.values():
      if param.name not in kwargs:
        if hasattr(param, 'default') and param.default is not NotSet:
          # TODO (@NiklasRosenstein): Rely on the remote default?
          continue
        raise TypeError('{}() missing keyword argument "{}"'.format(
          __route.name, param.name))
      if param.is_file():
        files[param.name] = _get(param)
      else:
        value = kwargs[param.name]
        serialized_value = self._mapper.se(
          getattr(param, 'content_type', PATH_PARAMETER_CONTENT_TYPE),
          value,
          param.type_annotation,
          filename='{}({})'.format(__route.name, param.name))
        if param.is_path():
          path_parameters[param.name] = serialized_value
        elif param.is_header():
          headers[param.name] = serialized_value
        elif param.is_query():
          params[param.name] = serialized_value
        elif param.is_body():
          body = serialized_value
          headers['Content-Type'] = param.content_type
        else:
          raise RuntimeError('unexpected route param {!r}'.format(param))

    url = (
      self._base_url.rstrip('/') + '/' +
      __route.route.http.path.render(path_parameters).lstrip('/'))

    response = self._session.request(
      __route.route.http.method, url,
      headers=headers,
      params=params,
      data=body,
      files=files)

    if (response.status_code // 100) not in (2, 3):
      if response.headers.get('Content-Type') != __route.route.content_type:
        response.raise_for_status()
      raise self.mapper.dd(__route.route.content_type, response.content, ServiceException)

    if __route.return_.is_void():
      if response.status_code != 201:
        logger.warning('expected 201 response from route {!r}, got {}'.format(
          __route, response.status_code))
      return None
    elif __route.return_.is_passthrough():
      return response
    elif __route.return_.is_mapped():
      return self.mapper.dd(__route.return_.content_type, response.content, __route.return_.type_annotation)
    else:
      raise RuntimeError('unexpected route return {!r}'.format(__route.return_))


class RestRequestsClient:

  def __init__(
      self,
      base_url: str,
      user_agent: str = None,
      proxies: dict = None,
      mapper: MimeTypeMapper = None
      ) -> None:
    self.base_url = base_url
    self.user_agent = user_agent
    self.proxies = proxies
    self.mapper = mapper or MimeTypeMapper.default()

    self.session = requests.Session()
    self.session.headers['User-Agent'] = self.user_agent
    self.session.proxies = proxies

  def for_resource(self, prefix: str, resource: Interface) -> ResourceClient:
    assert len(get_routes(resource)) >= 1, "provides no routes"
    base_url = self.base_url.rstrip('/') + '/' + prefix.lstrip('/')
    return ResourceClient[resource](base_url, self.mapper, self.session)
