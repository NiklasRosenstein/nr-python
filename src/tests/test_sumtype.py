
from nr.types.sumtype import Constructor, Sumtype, member_of
from nr.types.structured import Field, FieldSpec, Object


def test_sumtypes():

  class Result(Sumtype):
    Loading = Constructor('progress')
    Error = Constructor('message')

    @Constructor
    class Ok(Object):
      __fields__ = ['filename', 'load']

      def say_ok(self):
        return 'Ok! ' + self.load()

    @member_of([Loading])
    def alert(self):
      return 'Progress: ' + str(self.progress)

    static_error_member = member_of([Error], 'This is a member on Error!')

  #assert not hasattr(Result, 'constructor')
  assert not hasattr(Result, 'alert')
  assert not hasattr(Result, 'static_error_member')

  x = Result.Loading(0.5)
  assert isinstance(x, Result)
  assert x.is_loading()
  assert not x.is_error()
  assert not x.is_ok()
  assert hasattr(x, 'alert')
  assert not hasattr(x, 'static_error_member')
  assert x.alert() == 'Progress: 0.5'
  assert x.progress == 0.5

  class MoreResult(Result):
    InvalidState = Constructor()

  assert MoreResult.Loading is not Result.Loading
  assert MoreResult.Error is not Result.Error
  assert MoreResult.Ok is not Result.Ok

  x = MoreResult.Loading(0.5)
  assert isinstance(x, Result)
  assert x.is_loading()
  assert not x.is_error()
  assert not x.is_ok()
  assert hasattr(x, 'alert')
  assert not hasattr(x, 'static_error_member')
  assert x.alert() == 'Progress: 0.5'
  assert x.progress == 0.5
  assert isinstance(x, MoreResult)
  assert not hasattr(x, 'say_ok')

  x = MoreResult.InvalidState()
  assert x.is_invalid_state()
  assert isinstance(x, MoreResult)
  assert not hasattr(x, 'say_ok')

  ok = MoreResult.Ok('/tmp/test.txt', lambda: 'Hello')
  assert hasattr(ok, 'say_ok')
  assert ok.say_ok() == 'Ok! Hello'


def test_sumtype_default():

  class MySumtype(Sumtype):
    A = Constructor('a')
    B = Constructor('b', 'c')
    __default__ = A

  assert type(MySumtype(42)) is MySumtype.A
  assert MySumtype(42).a == 42

  assert type(MySumtype.B(1, 2)) is MySumtype.B
  assert MySumtype.B(1, 2) == MySumtype.B(1, 2)
  assert MySumtype.B(1, 2).c == 2


def test_readme_example():

  class Filter(Sumtype):
    # Three ways to define constructors.
    # 1)
    Date = Constructor('min,max')
    # 2)
    Keyword = Constructor([
      Field(str, name='text')
    ])
    # 3)
    @Constructor
    class Duration(Object):
      value = Field(int, default=3600)
      def to_hours(self):
        return self.value / 3600.0

    # Enrich constructors with members.
    @member_of([Date, Keyword])
    def only_on_date_or_keyword(self):
      return 'The answer is 42'

  f = Filter.Keyword('building')
  assert isinstance(f, Filter)
  assert f.is_keyword()
  assert f.text == 'building'
  assert hasattr(f, 'only_on_date_or_keyword')
  assert f.only_on_date_or_keyword() == 'The answer is 42'

  f = Filter.Date(10, 42)
  assert isinstance(f, Filter)
  assert f.is_date()
  assert (f.min, f.max) == (10, 42)
  assert hasattr(f, 'only_on_date_or_keyword')
  assert f.only_on_date_or_keyword() == 'The answer is 42'

  f = Filter.Duration()
  assert isinstance(f, Filter)
  assert f.is_duration()
  assert f.value == 3600
  assert not hasattr(f, 'only_on_date_or_keyword')

  f = Filter.Duration(value=4759)
  assert f.value == 4759
  assert f.to_hours() == (4759 / 3600.0)
