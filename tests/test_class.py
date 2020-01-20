""" Tests for MemoClass """

from memoclass.memoclass import MemoClass, mutates
from memoclass.memoize import memomethod
import pytest

class PartialSum(MemoClass):
    def __init__(self, stored, **kwargs):
        super(PartialSum, self).__init__(
                mutable_attrs=["call_count"], **kwargs)
        self.stored = stored
        self.call_count = 0

    @memomethod
    def __call__(self, other):
        self.call_count += 1
        return self.stored + other

    @mutates
    def mutate(self):
        pass

    @classmethod
    def reset(cls):
        cls.__call__.clear_cache()

    @memomethod
    def call_twice(self, other):
        self(other)
        return self(other)


def test_cls():
    """ Make sure that the test class is working """
    assert PartialSum(5)(3) == 8

def test_cache():
    """ Make sure that the cache is working """
    PartialSum.reset()
    a = PartialSum(5)
    assert a(3) == 8
    a(3)
    assert a(5) == 10
    assert a.call_count == 2
    a = None

def test_mutate():
    """ Make sure that the mutates functionality is working """
    PartialSum.reset()
    a = PartialSum(5)
    assert a(3) == 8
    a.stored = 3
    assert a(3) == 6
    assert a.call_count == 2
    a.mutate()
    assert a(3) == 6
    assert a.call_count == 3

def test_disable():
    """ Make sure that disabling the cache works correctly """
    PartialSum.reset()
    a = PartialSum(5)
    a.disable_caches()
    a(3)
    a(3)
    assert a.call_count == 2

def test_lock():
    """ Make sure that locking works correctly """
    PartialSum.reset()
    a = PartialSum(5)
    a.disable_caches()
    with a.locked():
        a(3)
        a(3)
        assert a.call_count == 1
        with pytest.raises(ValueError):
            a.stored = 5
    a(3)
    a(3)
    assert a.call_count == 3
    with a.locked():
        a(3)
        assert a.call_count == 4

def test_lockedfunc():
    """ Make sure that a locking function works properly """
    PartialSum.reset()
    a = PartialSum(5)
    a.disable_caches()
    assert a.call_twice(3) == 8
    assert a.call_count == 1
