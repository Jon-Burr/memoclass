""" Tests for a class method """

from builtins import object
from memoclass.memoize import memoclsmethod
from inspect import isfunction
from future.utils import iteritems

call_count = 0
class Base(object):
    """ Base class for testing memoclsmethods """

    @memoclsmethod
    def list_methods(cls, include_base=True):
        """ List the methods on this class """
        global call_count
        call_count += 1
        if not include_base:
            return set(k for k, v in iteritems(cls.__dict__)
                       if isfunction(v) )
        else:
            return set().union(*(
                sub.list_methods(False) for sub in cls.mro()
                if issubclass(sub, Base)))

    def x(self):
        pass

    def y(self):
        pass

class Derived(Base):
    def y(self):
        pass

    def z(self):
        pass

def reset():
    global call_count
    call_count = 0
    Base.__dict__["list_methods"].clear_cache()

def test_method():
    """ Test that the test method returns the correct value """
    reset()
    assert Derived.list_methods() == set(('x', 'y', 'z'))

def test_count():
    """ Test that the count is correct, i.e. that the caching is applied """
    reset()
    Derived.list_methods()
    assert call_count == 3
    Base.list_methods()
    assert call_count == 4
    Derived.list_methods.clear_cache()
    Derived.list_methods()
    assert call_count == 6

def test_cache():
    """ Test the cache works, i.e. that the return value doesn't modify even if
        it should (without caching)
    """
    reset()
    Derived.list_methods()
    def a(self):
        pass
    Derived.a = a
    methods = Derived.list_methods()
    del Derived.a
    assert methods == set(('x', 'y', 'z'))
