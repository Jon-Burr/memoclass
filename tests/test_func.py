""" Tests for a standalone function """

from memoclass.memoize import memofunc
import copy

factorial_count = 0
@memofunc
def factorial(n):
    """ Get the factorial of a number """
    global factorial_count
    factorial_count += 1
    if n == 0:
        return 1
    return n*factorial(n-1)

@memofunc(on_return=copy.copy)
def build_list():
    """ Create and return a list """
    return [1, 2, 3]

@memofunc
def join_list(head, tail=[1, 2, 3]):
    """ Join two lists """
    return head + tail

@memofunc
def prod_args(*args, **kwargs):
    """ Silly little function that just returns its arguments

        This is to test that memoising a function including *args and **kwargs
        works
    """
    return (args, kwargs)

def reset():
    global factorial_count
    factorial_count = 0
    factorial.clear_cache()

def test_factorial():
    """ Ensure that the test function works """
    reset()
    assert factorial(5) == 120

def test_count():
    """ Test that the caching results in the right number of calls """
    # Reset the count as we don't know that this is the first test to run
    reset()
    factorial(5)
    # if factorial_count != 6:
    assert factorial_count == 6
    factorial(3)
    assert factorial_count == 6
    factorial(7)
    assert factorial_count == 8

def test_clear():
    """ Test that clearing the cache works """
    reset()
    factorial(5) # Count == 6
    factorial.clear_cache()
    factorial(5)
    assert factorial_count == 12

def test_disable():
    """ Test that disabling the cache works """
    reset()
    factorial(5) # Count == 6
    factorial.disable_cache()
    factorial(5)
    assert factorial_count == 12
    factorial.enable_cache()
    factorial(5)
    assert factorial_count == 12

def test_rmcache():
    """ Test that removing a single entry from a cache works """
    reset()
    factorial(5) # Count == 6
    factorial.rm_from_cache(5)
    factorial(5)
    assert factorial_count == 7

def test_onreturn():
    """ Ensure that specifying an 'on_return' function works """
    a = build_list()
    b = build_list()
    assert a is not b

def test_defaults():
    """ Ensure that default arguments are correctly treated """
    a = join_list([0])
    b = join_list([0], [1, 2, 3])
    assert a is b

def test_prod_args():
    """ Test the prod_args function """
    res = prod_args(1, 2, 'a', k1="Hello", k2="World")
    assert prod_args(1, 2, 'a', k2="World", k1="Hello") is res
    assert prod_args(1, 2, 'a') is not res
