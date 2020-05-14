
from nr.databind.core import Field, Struct, make_struct
import pytest


def test_struct_repr():
    class Person(Struct):
        name = Field(str, prominent=True)
        age = Field(int)
        address = Field(str, default=None)

    assert str(Person('John Wick', 48, 'Wicked St.')) == "Person(name='John Wick')"

    Person.__fields__['name'].prominent = False
    Person.__fields__._update_cache()

    assert str(Person('John Wick', 48, 'Wicked St.')) == "Person(name='John Wick', age=48, address='Wicked St.')"


def test_make_struct():
    Person = make_struct('Person', {
        'name': Field(str, prominent=True),
        'age': Field(int),
        'address': Field(str, default=None)
    })

    assert str(Person('John Wick', 48, 'Wicked St.')) == "Person(name='John Wick')"

    Person.__fields__['name'].prominent = False
    Person.__fields__._update_cache()

    assert str(Person('John Wick', 48, 'Wicked St.')) == "Person(name='John Wick', age=48, address='Wicked St.')"

    assert Person('a', 31, 'Foobar') == Person('a', 31, 'Foobar')
    assert Person('a', 31, 'Foobar') != Person('b', 31, 'Foobar')
    assert Person('a', 31, 'Foobar') != Person('a', 32, 'Foobar')
    assert Person('a', 31, 'Foobar') != Person('a', 31, 'Spameggs')


def test_unexpected_keyword_argument():
    Person = make_struct('Person', {
        'name': Field(str, prominent=True),
        'age': Field(int, default=24),
    })

    Person(name='John').name
    Person(name='John', age=40)
    with pytest.raises(TypeError) as exc:
        Person(name='John', foobar=None)
    assert str(exc.value) == 'Person() constructor received unexpected keyword argument \'foobar\''
    with pytest.raises(TypeError) as exc:
        Person(name='John', age=40, foobar=None)
    assert str(exc.value) == 'Person() constructor expected at max 2 arguments, got 3'
