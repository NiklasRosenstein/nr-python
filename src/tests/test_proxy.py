
from nr.types import abc, proxy


def test_local_proxy_iterable():
    p = proxy(lambda: None)
    assert p == None
    assert not isinstance(p, abc.Mapping)
    assert isinstance(p, abc.Iterable)  # An unfortunate but necessary behaviour

    NonIterableProxy = proxy.make_proxy_class('NonIterableProxy', exclude=['__iter__'])

    p = NonIterableProxy(lambda: None)
    assert p == None
    assert not hasattr(p, '__iter__')
    assert not hasattr(NonIterableProxy, '__iter__')
    assert not isinstance(p, abc.Mapping)
    assert not isinstance(p, abc.Iterable), NonIterableProxy.__mro__

    NonIterableLazyProxy = proxy.make_proxy_class('NonIterableLazyProxy', proxy.lazy_proxy, exclude=['__iter__'])

    @NonIterableLazyProxy
    def p():
        count[0] += 1
        return count[0]

    count = [0]
    assert p == 1
    assert p == 1
    assert p == 1
    assert not hasattr(p, '__iter__')
    assert not hasattr(NonIterableProxy, '__iter__')
    assert not isinstance(p, abc.Mapping)
    assert not isinstance(p, abc.Iterable), NonIterableProxy.__mro__
