
from nr.databind.core.datatypes import *
from typing import Union


def test_union_to_multitype():
  datatype = translate_type_def(Union[str, int])
  assert datatype == MultiType([str, int])
