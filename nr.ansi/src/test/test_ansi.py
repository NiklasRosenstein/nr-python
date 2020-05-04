
from nr.ansi import *


def test_parse_color_sgrcolor():
  assert parse_color('RED') == SgrColor(SgrColorName.RED, False)
  assert parse_color('BRIGHT_RED') == SgrColor(SgrColorName.RED, True)
  assert parse_color('DEFAULT') == SgrColor(SgrColorName.DEFAULT, False)


def test_parse_color_lutcolor():
  assert parse_color('%024') == LutColor.from_rgb(0, 2, 4)
  assert parse_color('%000') == LutColor(16)
  assert parse_color('%555') == LutColor(231)
  assert parse_color('$127') == LutColor(127)
  assert parse_color('$3') == LutColor(3)


def test_parse_color_truecolor():
  assert parse_color('#0104ff') == TrueColor(0x1, 0x4, 0xff)
  assert parse_color('#14f') == TrueColor(0x11, 0x44, 0xff)


def test_parse_style_attribute():
  assert parse_style('UNDERLINE') == Style(attrs=[Attribute.UNDERLINE])
  assert parse_style('ENCIRCLED') == Style(attrs=[Attribute.ENCIRCLED])


def test_parse_style_foreground():
  assert parse_style('fg:%025') == Style(fg=LutColor.from_rgb(0, 2, 5))
  assert parse_style('fg:BRIGHT_MAGENTA') == Style(fg=SgrColor(SgrColorName.MAGENTA, True))


def test_parse_style_background():
  assert parse_style('bg:%025') == Style(bg=LutColor.from_rgb(0, 2, 5))
  assert parse_style('bg:BRIGHT_MAGENTA') == Style(bg=SgrColor(SgrColorName.MAGENTA, True))
