# -*- coding: utf-8 -*-
# MIT License
#
# Copyright (c) 2020, Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# this software and associated documentation files (the "Software"), to deal in
# Software without restriction, including without limitation the rights to use,
# modify, merge, publish, distribute, sublicense, and/or sell copies of the
# and to permit persons to whom the Software is furnished to do so, subject to
# following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR
# USE OR OTHER DEALINGS IN THE SOFTWARE.

from nr.pylang.utils import classdef, NotSet
from typing import Iterable, List, Union
import abc
import enum
import re

__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
__version__ = '0.0.2'


class Color(metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def as_foreground(self) -> str:
    ...

  @abc.abstractmethod
  def as_background(self) -> str:
    ...


class SgrColorName(enum.Enum):
  BLACK = 0
  RED = 1
  GREEN = 2
  YELLOW = 3
  BLUE = 4
  MAGENTA = 5
  CYAN = 6
  WHITE = 7
  DEFAULT = 9


class SgrColor(Color):

  classdef.comparable('name,bright')
  classdef.repr('name,bright')

  def __init__(self, name: SgrColorName, bright: bool = False) -> None:
    if isinstance(name, str):
      name = SgrColorName[name.upper()]
    self.name = name
    self.bright = bright

  def as_foreground(self) -> str:
    return str((90 if self.bright else 30) + self.name.value)

  def as_background(self) -> str:
    return str((100 if self.bright else 40) + self.name.value)


class LutColor(Color):

  classdef.comparable('index')
  classdef.repr('index')

  def __init__(self, color_index: int) -> None:
    self.index = color_index

  def as_foreground(self) -> str:
    return '38;5;' + str(self.index)

  def as_background(self) -> str:
    return '48;5;' + str(self.index)

  @classmethod
  def from_rgb(cls, r: int, g: int, b: int) -> 'LutColor':
    """
    Given RGB values in the range of [0..5], returns a #LutColor pointing
    to the color index that resembles the specified color coordinates.
    """

    def _check(name, value):
      if not (0 <= value < 6):
        raise ValueError('bad value for parameter "{}": {} ∉ [0..5]'.format(name, value))

    _check('r', r)
    _check('g', g)
    _check('b', b)

    return cls((16 + 36 * r) + (6 * g) + b)


class TrueColor(Color):

  classdef.comparable('r,g,b')
  classdef.repr('r,g,b')

  def __init__(self, r: int, g: int, b: int) -> None:
    self.r = r
    self.g = g
    self.b = b

  def as_foreground(self) -> str:
    return '38;2;{};{};{}'.format(self.r, self.g, self.b)

  def as_background(self) -> str:
    return '48;2;{};{};{}'.format(self.r, self.g, self.b)


def parse_color(color_string: str) -> Color:
  """
  Parses a color string of one of the following formats and returns a
  corresponding #SgrColor, #LutColor or #TrueColor.

  * `<color_name>`, `BRIGHT_<color_name>`: #SgrColor
  * `%rgb`, `$xxx`: #LutColor
  * `#cef`, `#cceeff`: #TrueColor
  """

  if color_string.startswith('%') and len(color_string) == 4:
    try:
      r, g, b = map(int, color_string[1:])
    except ValueError:
      pass
    else:
      if r < 6 and g < 6 and b < 6:
        return LutColor.from_rgb(r, g, b)

  elif color_string.startswith('$') and len(color_string) <= 4:
    try:
      index = int(color_string[1:])
    except ValueError:
      pass
    else:
      if index >= 0 and index < 256:
        return LutColor(index)

  elif color_string.startswith('#') and len(color_string) in (4, 7):
    parts = re.findall('.' if len(color_string) == 4 else '..', color_string[1:])
    if len(color_string) == 4:
      parts = [x*2 for x in parts]
    try:
      parts = map(lambda x: int(x, 16), parts)
    except ValueError:
      pass
    else:
      return TrueColor(*parts)

  else:
    color_string = color_string.upper()
    bright = color_string.startswith('BRIGHT_') or color_string.startswith('BRIGHT ')
    if bright:
      color_string = color_string[7:]
    if hasattr(SgrColorName, color_string):
      return SgrColor(SgrColorName[color_string], bright)

  raise ValueError('unrecognized color string: {!r}'.format(color_string))


class Component(metaclass=abc.ABCMeta):

  def __str__(self) -> str:
    return to_escape_sequence(self)

  @abc.abstractmethod
  def to_escape_code(self) -> str:
    ...


class Attribute(enum.Enum):  # Should inherit from Component
  RESET = 0
  BOLD = 1
  FAINT = 2
  ITALIC = 3
  UNDERLINE = 4
  SLOW_BLINK = 5
  RAPID_BLINK = 6
  REVERSE_VIDEO = 7
  CONCEAL = 8
  CROSSED_OUT = 9
  FONT_0 = 10
  FONT_1 = 11
  FONT_2 = 12
  FONT_3 = 13
  FONT_4 = 14
  FONT_5 = 15
  FONT_6 = 16
  FONT_7 = 17
  FONT_8 = 18
  FONT_9 = 19
  FRAKTUR = 20
  DOUBLY_UNDERLINE = 21
  NORMAL_INTENSITY = 22
  NOT_ITALIC = 23
  UNDERLINE_OFF = 24
  BLINK_OFF = 25
  REVERSE_OFF = 27
  REVEAL = 28
  CROSSED_OUT_OFF = 29
  FRAMED = 51
  ENCIRCLED = 52
  OVERLINED = 53
  FRAMED_OFF = 54
  OVERLINED_OFF = 55

  __str__ = Component.__str__

  def to_escape_code(self) -> str:
    return str(self.value)


class _ColorWrapper(Component):

  classdef.comparable('color')
  classdef.repr('color')

  def __init__(self, color: Union[Color, str]):
    if isinstance(color, str):
      color = parse_color(color)
    self.color = color


class Foreground(_ColorWrapper):

  def to_escape_code(self) -> str:
    return self.color.as_foreground()


class Background(_ColorWrapper):

  def to_escape_code(self) -> str:
    return self.color.as_background()


def to_escape_sequence(*seq: Union[Component, str, None]) -> str:
  result = '\033['
  for item in seq:
    if item is None:
      continue
    if isinstance(item, str):
      item = parse_component(item)
    result += item.to_escape_code() + ';'
  return result.rstrip(';') + 'm'


class Style:

  classdef.comparable('fg,bg,attrs')
  classdef.repr('fg,bg,attrs')

  def __init__(
      self,
      fg: Union[Color, str] = None,
      bg: Union[Color, str] = None,
      attrs: List[Attribute] = None
      ) -> None:

    if isinstance(fg, str):
      fg = parse_color(fg)
    if isinstance(bg, str):
      bg = parse_color(bg)
    attrs = [Attribute[k.upper()] if isinstance(k, str) else k for k in attrs or ()]

    assert fg is None or isinstance(fg, Color), type(fg)
    assert bg is None or isinstance(bg, Color), type(bg)

    self.fg = fg
    self.bg = bg
    self.attrs = attrs

  def __str__(self):
    fg = Foreground(self.fg) if self.fg else None
    bg = Background(self.bg) if self.bg else None
    return to_escape_sequence(fg, bg, *self.attrs)

  def merge(self, other: 'Style') -> 'Style':
    """
    Merge two styles, taking precedence to the color and attributes of *self*.
    """

    return Style(self.fg or other.fg, self.bg or other.bg,
      other.attrs + self.attrs)

  def replace(self, fg=NotSet, bg=NotSet, attrs=NotSet) -> 'Style':
    fg = self.fg if fg is NotSet else fg
    bg = self.bg if bg is NotSet else bg
    attrs = self.attrs if attrs is NotSet else attrs
    return Style(fg, bg, attrs)


def parse_style(style_string: str) -> Style:
  """
  Parses a style string, returning a #Style object with the foreground and
  background color and the attributes per the string. A style string is a
  sequence of words each of one of the following formats:

  * `fg:<color_string>`: #Foreground
  * `bg:<color_string>`: #Background
  * `<attribute_name>`: #Attribute

  The `fg:` and `bg:` suffixes may be omitted and the colors are then
  assigned in order, to the foreground first.
  """

  fg = None
  bg = None
  attrs = []

  for component in style_string.split():

    component_upper = component.upper()
    if hasattr(Attribute, component_upper):
      attrs.append(Attribute[component_upper])
      continue

    if component.startswith('fg:'):
      fg = parse_color(component[3:])
      continue
    if component.startswith('bg:'):
      bg = parse_color(component[3:])
      continue

    try:
      color = parse_color(component)
    except ValueError:
      pass
    else:
      if not fg:
        fg = color
      elif not bg:
        bg = color
      else:
        raise ValueError('unexpected third color component: {!r}'.format(component))
      continue

    raise ValueError('unrecognized component: {!r}'.format(component))

  return Style(fg, bg, attrs)


def styled(text: str, *args, **kwargs) -> str:
  """
  Returns *text* enclosed in ANSI escape codes for the specified foreground
  and background color and attributes. The *args* and *kwargs* are passed
  directly to the #Style constructor.
  """

  style = Style(*args, **kwargs)
  return str(style) + text + str(Attribute.RESET)
