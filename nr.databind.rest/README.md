# nr.databind.rest

This module can be used to define a REST API interface using Python 3
annotations and `nr.databind` object mapping features.

*Todo*

* [ ] Dynamic and static code generation for REST clients

### Example

Resources are created by defining an `Interface` subclass and decorating its
methods with the `@Route` decorator. The subclass can then be used to
automatically generate client code and to implement a server based on the
same interface.

```py
from my.service.api.types import MyRequest, MyResponse
from nr.databind.rest import Route, RouteParam
from nr.interface import Interface

class MyResource(Interface):

  @Route('GET /my-endpoint/{parameter_a}')
  def my_get_endpoint(self, parameter_a: str, parameter_b: QP(int)) -> MyResponse:
    ...

  @Route('POST /my-endpoint/{parameter_a}')
  def my_post_endpoint(self, parameter_a: str, body: MyRequest) -> MyResponse:
    ...
```

The resource is then implemented like this:

```py
from my.service.api.resources import MyResource
from my.service.api.types import MyResponse
from nr.interface import implements


@implements(MyResource)
class MyResourceImpl:

  def my_get_endpoint(self, parameter_a, parameter_b):
    # ...
    return MyResponse(...)
  
  def my_post_endpoint(self, parameter_a, body):
    # ...
    return MyResponse(...)
```

Resources can then be bound to a server framework using one of the available
bind mechanisms (currently only Flask is available).

```py
from flask import Flask
from my.service.api.resources_impl import MyResourceImpl
from nr.databind.json import JsonModule
from nr.databind.rest.flask import bind_resource, FlaskRequestMapper

app = Flask(__name__)
request_mapper = FlaskRequestMapper(JsonModule())
bind_resource(request_mapper, app, '/my-resource', MyResourceImpl)
```
