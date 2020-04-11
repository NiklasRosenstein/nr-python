
import flask
import unittest

from nr.databind.core import Field, Struct
from nr.databind.rest import get_routes, Route, RouteParam, InvalidArgument
from nr.databind.rest.flask import bind_resource
from nr.interface import implements, Interface



class IncrementPayload(Struct):
  value = Field(int)


class MyResource(Interface):

  @Route('GET /multiply/{a}/by/{b}')
  def multiply_by(self, a: int, b: int) -> int:
    ...

  @Route('POST /increment-payload')
  def increment_payload(self, body: IncrementPayload) -> IncrementPayload:
    ...

  @Route('PUT /no-response')
  def query_param_no_response(self, param: RouteParam.Query(int)) -> None:
    ...

  @Route('PUT /no-response/optional')
  def query_param_no_response_optional(self, param: RouteParam.Query(int) = 0) -> None:
    ...


@implements(MyResource)
class MyResourceImpl:

  def multiply_by(self, a, b):
    return a * b

  def increment_payload(self, body):
    body.value += 1
    return body

  def query_param_no_response(self, param):
    if param != 3:
      raise InvalidArgument('Expected value of "param" to be 3.')

  def query_param_no_response_optional(self, param):
    if param == 0:
      raise InvalidArgument('This matches the default argument')
    elif param == 3:
      raise InvalidArgument('This matches 3')


class FlaskResourceTest(unittest.TestCase):

  def setUp(self):
    self.app = flask.Flask('')
    self.client = self.app.test_client()
    bind_resource(self.app, '', MyResourceImpl())

  def test_multiply_by(self):
    response = self.client.get('/multiply/42/by/3')
    assert response.status_code == 200
    assert response.is_json
    assert response.get_json() == (42 * 3)

  def test_increment_payload(self):
    response = self.client.post('/increment-payload', json={'value': 7})
    assert response.status_code == 200
    assert response.is_json
    assert response.get_json() == {'value': 8}

  def test_query_param_no_response(self):
    response = self.client.put('/no-response', query_string={'param': 3})
    assert response.status_code == 201

    response = self.client.put('/no-response', query_string={'param': 5})
    assert response.status_code == 400
    assert response.is_json
    payload = response.get_json()
    payload.pop('errorUuid')
    assert payload == {
      'errorType': 'nr.databind.rest:InvalidArgument',
      'errorMessage': 'Expected value of "param" to be 3.',
    }

    response = self.client.put('/no-response')
    assert response.status_code == 400
    assert response.is_json
    payload = response.get_json()
    payload.pop('errorUuid')
    assert payload == {
      'errorType': 'nr.databind.rest:BadRequest',
      'errorMessage': 'missing required query parameter',
      'errorParameters': {'queryParam': 'param'}
    }

  def test_query_param_no_response_optional(self):
    response = self.client.put('/no-response/optional')
    assert response.status_code == 400
    assert response.is_json
    payload = response.get_json()
    payload.pop('errorUuid')
    assert payload == {
      'errorType': 'nr.databind.rest:InvalidArgument',
      'errorMessage': 'This matches the default argument',
    }

    response = self.client.put('/no-response/optional', query_string={'param': 3})
    assert response.status_code == 400
    assert response.is_json
    payload = response.get_json()
    payload.pop('errorUuid')
    assert payload == {
      'errorType': 'nr.databind.rest:InvalidArgument',
      'errorMessage': 'This matches 3',
    }
