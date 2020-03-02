# -*- coding: utf8 -*-
# Copyright (c) 2019 Niklas Rosenstein
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


def _unique_and_chain(*iterables):
  seen = set()
  for iterable in iterables:
    for value in iterable:
      if value not in seen:
        seen.add(value)
        yield value


def get_conflicting_metaclasses(metaclasses=(), bases=()):
  """ Checks if any of classes in *metaclasses* are conflicting (or any of
  the metaclasses of *bases*). Returns a list of conflicting metaclasses. """

  metaclasses = tuple(_unique_and_chain(metaclasses, map(type, bases)))
  conflicts = []
  for x in metaclasses:
    for y in metaclasses:
      if x is y: continue
      if not (issubclass(x, y) or issubclass(y, x)):
        if x not in conflicts:
          conflicts.append(x)
        if y not in conflicts:
          conflicts.append(y)
  return conflicts


def resolve_metaclass_conflict(metaclasses=(), bases=(), _cache={}):
  """ Resolves a metaclass conflict for the specified *bases*. Note that this
  will not check if there is a conflict and simply produce a new metaclass
  that combines the metaclasses of *metaclasses* or *bases*. """

  metaclasses = tuple(_unique_and_chain(metaclasses, map(type, bases)))
  if metaclasses in _cache:
    return _cache[metaclasses]

  name = '_' + '_'.join(x.__name__ for x in metaclasses)
  result = type(name, metaclasses, {})
  _cache[metaclasses] = result
  return result


def reduce_mro(*classes):
  """ Reduces a list of classes to the essential list, removing any redundent
  parent classes. """

  result = list(classes)
  for x in classes:
    for y in classes:
      if x is y: continue
      if issubclass(x, y):
        result.remove(y)

  return tuple(result)


def deconflict_bases(*bases):  # type: (Tuple[Type]) -> Tuple[Type]
  """ If the metaclasses of *bases* conflict, the conflict will be resolved
  and a new parent class will be created. Otherwise, *bases* is returned as
  is. Example usage:

  ```python
  class MyClass(*deconflict_bases(BaseclassA, BaseclassB)):
    # ...
  ``` """

  bases = reduce_mro(*bases)
  if not get_conflicting_metaclasses(bases=bases):
    return bases

  metaclass = resolve_metaclass_conflict(bases=bases)
  name = 'deconflict_' + '_'.join(map(lambda x: x.__name__, bases))
  parent_cls = metaclass(name, bases, {})
  return (parent_cls,)


def deconflicted_base(*bases):  # type: (Tuple[Type]) -> Type:
  bases = deconflict_bases(*bases)
  if len(bases) == 1:
    return bases[0]
  else:
    name = '_' + '_'.join(x.__name__ for x in bases)
    return type(name, bases, {})
