""" Tests for a class' method """

from builtins import object
from memoclass.memoize import memomethod

call_count = 0
class PartialSum(object):
    """ Functor that returns the sum of a stored number and a supplied number
    """

    def __init__(self, stored):
        self.stored = stored

    @memomethod
    def __call__(self, other):
        global call_count
        call_count += 1
        return self.stored + other

def reset():
    global call_count
    PartialSum.__call__.clear_cache()
    call_count = 0

def test_call():
    """ Test to make sure that the test function is correct """
    assert PartialSum(5)(3) == 8

def test_count():
    """ Test to make sure that the cache works """
    reset()
    a = PartialSum(5)
    a(3)
    a(3)
    assert call_count == 1

def test_shared():
    """ Test to make sure that two objects don't share the same caches """
    reset()
    a = PartialSum(5)
    b = PartialSum(5)
    a(3)
    b(3)
    assert call_count == 2

def test_cache():
    """ Test to make sure that the caching works """
    # NB: This test actually exploits a weakness in the PartialSum object. Using
    # this behaviour (changing a class without reset the cache) would be a
    # rather obvious bug in real code
    reset()
    a = PartialSum(5)
    a(3)
    a.stored = 3
    # Should retrieve the old value
    assert a(3) == 8
    # Should calculate a new value
    assert a(2) == 5

def test_clear():
    """ Test to make sure that clearing the cache on one object doesn't affect
        another
    """
    reset()
    a = PartialSum(5)
    b = PartialSum(5)
    a(3)
    b(3)
    a.__call__.clear_cache()
    b(3)
    assert call_count == 2
    PartialSum.__call__.clear_cache(b)
    b(3)
    assert call_count == 3

def test_garbage():
    """ Test to make sure that garbage collection catches any relevant caches
    """
    reset()
    a = PartialSum(5)
    a(3)
    assert len(PartialSum.__call__._bound_caches) == 1
    a = None
    assert len(PartialSum.__call__._bound_caches) == 0
