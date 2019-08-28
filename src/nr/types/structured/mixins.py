

class ToJSON(object):
  """
  A mixin for the #CleanRecord class that adds a #to_json() method.
  Different from the #as_dict() method in the #AsDict mixin, #to_json()
  is called recursively on any of the attributes if they have a #to_json()
  method.
  """

  def to_json(self):
    """
    Converts the record to a representation that can be dumped into JSON
    format. For any member, it will check if that member has a `to_json()`
    method and call it. Mappings and sequences are converted recursively.

    Note that this method does not guarantee that the returned object will
    be JSON serializable afterwards. For special cases, the method should
    be overwritten.
    """

    def coerce(value):
      if hasattr(value, 'to_json'):
        return value.to_json()
      elif isinstance(value, abc.Mapping):
        return dict((k, value[k]) for k in value)
      elif isinstance(value, abc.Sequence) and not isinstance(value, (six.string_types, six.binary_type, bytearray)):
        return [coerce(x) for x in value]
      else:
        return value

    result = {}
    for key in self.__fields__:
      result[key] = coerce(getattr(self, key))
    return result


class AsDict(object):
  """
  A mixin for the #CleanRecord class that adds an #as_dict() method.
  """

  def as_dict(self):
    return dict((k, getattr(self, k)) for k in self.__fields__)


class Sequence(object):
  """
  A mixin for the #CleanRecord class that implements the mutable sequence
  interface.
  """

  def __iter__(self):
    for key in self.__fields__:
      yield getattr(self, key)

  def __len__(self):
    return len(self.__fields__)

  def __getitem__(self, index):
    if hasattr(index, '__index__'):
      return getattr(self, self.__fields__[index.__index__()].name)
    elif isinstance(index, str):
      return getattr(self, str)
    else:
      raise TypeError('cannot index with {} object'
        .format(type(index).__name__))

  def __setitem__(self, index, value):
    if hasattr(index, '__index__'):
      setattr(self, self.__fields__[index.__index__()].name, value)
    elif isinstance(index, str):
      setattr(self, index, value)
    else:
      raise TypeError('cannot index with {} object'
        .format(type(index).__name__))
