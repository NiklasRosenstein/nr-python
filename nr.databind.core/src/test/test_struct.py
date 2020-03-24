
from nr.databind.core import Field, Struct, make_struct


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

