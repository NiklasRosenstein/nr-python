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

"""
A fast date parser library with timezone offset support.
"""

from datetime import datetime, timedelta, tzinfo
from itertools import chain
import abc
import importlib
import io
import os
import six
import warnings

# Python 2 compatibility
try:
	unicode
	StringIO = io.BytesIO
except NameError:
	StringIO = io.StringIO

re = importlib.import_module(os.getenv('PYTHON_NR_DATE_REGEX_BACKEND', 're'))

__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
__version__ = '0.1.0'


class timezone(tzinfo):
	"""
	A simple implementation of #datetime.tzinfo.
	"""

	_ZERO = timedelta(0)

	def __init__(self, name, offset):  # type: (Optional[str], Union[timedelta, int]) -> None
		offset = offset.total_seconds() if hasattr(offset, 'total_seconds') else int(offset)
		self._offset = timedelta(seconds=offset)
		self._name = name
		if offset == 0 and not self._name:
			self._name = 'UTC'

	def dst(self, dt):
		return self._ZERO

	def utcoffset(self, dt):
		return self._offset

	def tzname(self, dt):
		return self._name

	def fromutc(self, dt):
		return dt + self._offset

	def __repr__(self):
		if self._name == 'UTC':
			return 'timezone.utc'
		else:
			return 'timezone({!r}, {!r})'.format(self._name, self._offset.total_seconds())

	def __eq__(self, other):
		if not isinstance(other, timezone):
			return NotImplemented
		return self._offset == other._offset

	def __ne__(self, other):
		return not (self == other)

	def __hash__(self):
		return hash((type(self), self._offset))


timezone.utc = timezone('UTC', 0)


class BaseFormatOption(object):

	def __init__(self, char, dest):
		self.char = char
		self.dest = dest

	def parse(self, string):
		raise NotImplementedError

	def render(self, date):
		raise NotImplementedError


class FormatOption(BaseFormatOption):

	def __init__(self, char, dest, regex, parse, render):
		super(FormatOption, self).__init__(char, dest)
		self.regex = re.compile(regex)
		self.parse = parse
		self.render = render


class TimezoneFormatOption(BaseFormatOption):

	def __init__(self, char='z', dest='tzinfo'):
		super(TimezoneFormatOption, self).__init__(char, dest)
		self.regex = re.compile(r'(?:Z|[-+]\d{2}:?\d{2})')

	def parse(self, string):
		match = self.regex.match(string)
		if not match:
			raise ValueError('not a timezone string: {!r}'.format(string))
		if string == 'Z':
			return timezone.utc
		else:
			string = string.replace(':', '')
			sign = -1 if string[0] == '-' else 1
			hours = int(string[1:3])
			minutes = int(string[3:5])
			seconds = sign * (hours * 3600 + minutes * 60)
			return timezone(None, seconds)

	def render(self, date):
		if date.tzinfo == None:
			raise ValueError('no tzinfo in date: {!r}'.format(date))
		elif date.tzinfo == timezone.utc:
			return 'Z'
		else:
			off = date.utcoffset()
			# NOTE Copied from CPython 3.7 datetime.py _format_offset()
			string = ''
			if off is not None:
				if off.days < 0:
					sign = "-"
					off = -off
				else:
					sign = "+"
				off = off.total_seconds()
				hh, mm = divmod(off, 60 * 60)
				mm, ss = divmod(mm, 60)
				ss, ms = divmod(ss, 1)
				string += "%s%02d:%02d" % (sign, hh, mm)
				if ss or ms:
					string += ":%02d" % ss
					if ms:
						string += '.%06d' % ms
			return string


class FormatOptionSet(object):

	def __init__(self, options=()):
		self._options = {}
		self._cache = {}
		for option in options:
			self.add(option)

	def __repr__(self):
		return 'FormatOptionSet({})'.format(''.join(sorted(self._options)))

	def __getitem__(self, char):
		return self._options[char]

	def __contains__(self, char):
		return char in self._options

	def add(self, option):
		if not isinstance(option, BaseFormatOption):
			raise TypeError('expected BaseFormatOption')
		if option.char in self._options:
			raise ValueError('format char {!r} already allocated'.format(option.char))
		self._options[option.char] = option

	def create_date_format(self, fmt):
		# TODO @NiklasRosenstein Work around cyclic reference, eg. with a weakref?
		try:
			return self._cache[fmt]
		except KeyError:
			obj = self._cache[fmt] = DateFormat(fmt, self)
			return obj

	def create_format_set(self, name, formats):
		formats = [self.create_date_format(x) if not isinstance(x, DateFormat) else x for x in formats]
		return DateFormatSet(name, formats)

	def parse(self, string, fmt):
		return self.create_date_format(fmt).parse(string)

	def format(self, date, fmt):
		return self.create_date_format(fmt).format(date)


class DateFormat(object):
	"""
	Represents a fully compiled fixed date format ready to parse and
	format dates.
	"""

	def __init__(self, string, option_set):
		index = 0
		pattern = StringIO()
		options = []
		join_sequence = []
		def write(char):
			pattern.write(re.escape(string[index]))
			if join_sequence and isinstance(join_sequence[-1], str):
				join_sequence[-1] += string[index]
			else:
				join_sequence.append(string[index])
		while index < len(string):
			if string[index] == '%':
				char = string[index+1]
				if char != '%' and char not in option_set:
					raise ValueError('Invalid date format "%{}"'.format(char))
				fo = option_set[char]
				if char == '%':
					write('%')
				else:
					pattern.write('(' + fo.regex.pattern + ')')
					options.append(fo)
					join_sequence.append(fo)
				index += 2
			else:
				write(string[index])
				index += 1

		self._string = string
		self._regex = re.compile(pattern.getvalue())
		self._join_sequence = join_sequence
		self._options = options

	def __repr__(self):
		return 'DateFormat(string={!r})'.format(self.string)

	@property
	def string(self):
		return self._string

	def parse(self, string):
		match = self._regex.match(string)
		if not match:
			raise ValueError('Date "{}" does not match format {!r}'.format(
				string, self.string))
		kwargs = {'year': 1900, 'month': 1, 'day': 1, 'hour': 0}
		for option, value in zip(self._options, match.groups()):
			kwargs[option.dest] = option.parse(value)
		return datetime(**kwargs)

	def format(self, date):
		result = StringIO()
		for item in self._join_sequence:
			if isinstance(item, str):
				result.write(item)
			else:
				result.write(item.render(date))
		return result.getvalue()


class DateFormatSet(list):
	"""
	Represents a set of date formats.
	"""

	def __init__(self, name, formats):
		self.name = name
		super(DateFormatSet, self).__init__(formats)

	def __repr__(self):
		return 'DateFormatSet({!r}, {})'.format(
			self.name, super(DateFormatSet, self).__repr__())

	def parse(self, string):
		for fmt in self:
			try:
				return fmt.parse(string)
			except ValueError as exc:
				pass
		msg = 'Date "{}" does not match any of the {!r} formats.\n- {}'
		formats = '\n- '.join(x.string for x in self)
		raise ValueError(msg.format(string, self.name, formats))

	def format(self, date):
		errors = []
		for fmt in self:
			try:
				return fmt.format(date)
			except ValueError as exc:
				errors.append(exc)
		msg = 'Date "{}" cannot be formatted with any of the {!r} formats.\n- {}'
		formats = '\n- '.join('{}: {}'.format(x.string, e) for x, e in zip(self, errors))
		raise ValueError(msg.format(date, self.name, formats))


root_option_set = FormatOptionSet([
    FormatOption('Y', 'year', r'\d{4}', int, lambda d: str(d.year).rjust(4, '0')),
    FormatOption('m', 'month', r'\d{2}', int, lambda d: str(d.month).rjust(2, '0')),
    FormatOption('d', 'day', r'\d{2}', int, lambda d: str(d.day).rjust(2, '0')),
    FormatOption('H', 'hour', r'\d{2}', int, lambda d: str(d.hour).rjust(2, '0')),
    FormatOption('M', 'minute', r'\d{2}', int, lambda d: str(d.minute).rjust(2, '0')),
    FormatOption('S', 'second', r'\d{2}', int, lambda d: str(d.second).rjust(2, '0')),
    FormatOption('f', 'microsecond', r'\d+', lambda s: int(s) * (10 ** max(6-len(s), 0)), lambda d: str(d.microsecond).rstrip('0') or '0'),
    TimezoneFormatOption(),
])


def register_format_option(option):
	root_option_set.add(option)


def parse_date(string, fmt):
	return root_option_set.parse(string, fmt)


def format_date(date, fmt):
	return root_option_set.format(date, fmt)


def parse_iso8601_duration(d):  # type: (str) -> int
	" Parses an ISO8601 duration to seconds. Thanks to https://stackoverflow.com/a/35936407 "

	if d[0] != 'P':
		raise ValueError('Not an ISO 8601 Duration string')

	seconds = 0
	for i, item in enumerate(d.split('T')):
		for number, unit in re.findall(r'(?P<number>\d+)(?P<period>S|M|H|D|W|Y)', item ):
			number = int(number)
			this = 0
			if unit == 'Y':
				this = number * 31557600 # 365.25
			elif unit == 'W':
				this = number * 604800
			elif unit == 'D':
				this = number * 86400
			elif unit == 'H':
				this = number * 3600
			elif unit == 'M':
				# ambiguity ellivated with index i
				if i == 0:
					this = number * 2678400  # assume 30 days
				else:
					this = number * 60
			elif unit == 'S':
				this = number
			seconds = seconds + this
	return seconds


@six.add_metaclass(abc.ABCMeta)
class DatetimeFormat(object):

	@abc.abstractmethod
	def parse(self, string):  # type: (str) -> datetime
		pass

	@abc.abstractmethod
	def format(self, datetime):  # type: (datetime) -> str
		pass


class Iso8601(DatetimeFormat):

	_format_set = root_option_set.create_format_set('Iso8601', [
		'%Y-%m-%dT%H:%M:%S.%f%z',  # RFC 3339
		'%Y-%m-%dT%H:%M:%S.%f',    # ISO 8601 extended format
		'%Y%m%dT%H%M%S.%f',        # ISO 8601 basic format
		'%Y%m%d',                  # ISO 8601 basic format, date only
	])

	def parse(self, string):
		return self._format_set.parse(string)

	def format(self, datetime):
		return self._format_set.format(datetime)


class JavaOffsetDatetime(DatetimeFormat):

	_standard = root_option_set.create_format_set('JavaOffsetDatetime', [
		'%Y-%m-%dT%H:%M:%S.%f%z',
		'%Y-%m-%dT%H:%M:%S%z',
		'%Y-%m-%dT%H:%M%z',
	])

	_optional_tz = root_option_set.create_format_set('JavaOffsetDatetime',
		chain(*zip(_standard, [x.string[:-2] for x in _standard])))

	def __init__(self, require_timezone=True):
		self.require_timezone = require_timezone
		self._format_set = self._standard if require_timezone else self._optional_tz

	def parse(self, string):
		return self._format_set.parse(string)

	def format(self, datetime):
		return self._format_set.format(datetime)
