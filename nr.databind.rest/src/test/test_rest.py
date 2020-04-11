
import pytest

from nr.databind.rest import *
from nr.interface import Interface
from nr.pylang.utils import NotSet


def test_http_data():
  assert HttpData.parse('GET /my-endpoint/{myParameter}') == HttpData('GET', Path('/my-endpoint/{myParameter}'))


def test_path():
  assert str(Path('/my-endpoint/{myParameter}')) == '/my-endpoint/{myParameter}'
  assert Path('/my-endpoint/{myParameter}').parameters == ['myParameter']
  assert Path('/my-endpoint/{myParameter}/{b}').parameters == ['myParameter', 'b']

  with pytest.raises(ValueError):
    assert Path('/my-endpoint/{a}/{a}')


def test_route_decorator():
  with pytest.raises(ValueError, match='missing parameter \'c\' in function "foo"'):
    @Route('GET /my-endpoint/{a}/{b}/{c}')
    def foo(a, b):
      pass

  class MyResource(Interface):

    @Route('GET /{a}/foo/{b}')
    def foo(self, a, b: str):
      pass

    @Route('POST /set')
    def set(self):
      pass

  routes = get_routes(MyResource)
  assert routes[0] == ParametrizedRoute(
    'foo',
    RouteData(HttpData.parse('GET /{a}/foo/{b}'), 'application/json'),
    MyResource,
    {'a': RouteParam.Path(NotSet, 'a'), 'b': RouteParam.Path(str, 'b')},
    RouteReturn.Void()
  )
  assert routes[1] == ParametrizedRoute(
    'set',
    RouteData(HttpData.parse('POST /set'), 'application/json'),
    MyResource,
    {},
    RouteReturn.Void()
  )
