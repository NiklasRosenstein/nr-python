
from nr.types import sumtype


def test_sumtypes():

  class Result(sumtype):
    Loading = sumtype.constructor('progress')
    Error = sumtype.constructor('message')

    class Ok(sumtype.record):
      __fields__ = ['filename', 'load']

      def say_ok(self):
        return 'Ok! ' + self.load()

    @sumtype.member_of([Loading])
    def alert(self):
      return 'Progress: ' + str(self.progress)

    static_error_member = sumtype.member_of([Error], 'This is a member on Error!')

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
    InvalidState = sumtype.constructor()

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
