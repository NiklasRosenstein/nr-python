
from nr.databind.core import ObjectMapper
from nr.databind.json import JsonModule
import pytest


@pytest.fixture
def mapper():
  return ObjectMapper(JsonModule())
