""" Basic decoarators for memoizing functions and methods"""

from builtins import object
from functools import update_wrapper, partial
from inspect import getcallargs, isfunction, ismethod
from types import MethodType
from future.utils import iteritems, itervalues, PY3
if PY3:
    from collections.abc import MutableMapping
    from inspect import getfullargspec as getargspec
else:
    from collections import MutableMapping
    from inspect import getargspec

def _to_hashable(arg=None):
    """ Convert an argument into a hashable type

        If the argument has a '_to_hashable' function, that is called.

        If the argument is one of the mutable built in types the conversions are
        as follows:
            - set -> frozenset
            - list -> tuple
            - dict -> frozenset(dict.items() )

        Note that first the objects inside these objects will be converted using
        _to_hashable (this step isn't necessary for set as all set elements must
        be hashable by definition
    """
    if hasattr(arg, '_to_hashable'):
        return arg._to_hashable()
    elif isinstance(arg, set):
        return frozenset(arg)
    elif isinstance(arg, (tuple, list) ):
        return tuple(_to_hashable(element) for element in arg)
    elif isinstance(arg, dict):
        return frozenset((k, _to_hashable(v)) for k, v in iteritems(arg) )
    else:
        return arg

def make_decorator(decorator):
    def inner(func=None, **kwargs):
        if func is None:
            return partial(decorator, **kwargs)
        else:
            return decorator(func, **kwargs)
    return inner

class MemoFunc(object):
    """ Memoizes a free function """
    def __init__(self, func, cache_cls=dict, on_return=lambda x: x,
                 hasher=_to_hashable):
        """ Memoize a free function

            The locks and clear_on_unlock parameters can usually be ignored by
            users, they are used by the 'MemoMethod' class

            :param func: The function to memoize
            :param cache_cls: The type to use for caching, defaults to dict
            :param on_return: 
                An additional function called on the return value. The main use
                case for this is to supply a copy function, for the case when
                you memoize a function that returns a mutable type (like a list)
                that is constructed on the fly and shouldn't be persistent
                between calls, defaults to a lambda that just returns the value
                unmodified.
            :param hasher:
                The function that should be used to make the arguments hashable.
                It will receive the callargs dictionary as an argument if func
                satisifies inspect.isfunction, otherwise receives a two-tuple of
                (args, kwargs), defaults to _to_hashable
            :param locks:
                If True, the function *must* be called with an object supplied
                to the first argument that has a 'locked' method, taking one
                argument that is a context manager (will usually be a MemoClass
                object)
            :param clear_on_unlock:
                Parameter passed to the object in the first argument's locked()
                method if locks is set and used
        """
        update_wrapper(self, func)
        self._wrapped_func = func
        self._cache = cache_cls()
        self._on_return = on_return
        self._hasher = hasher
        self._cache_enabled = True
        # Select the right function to make the callargs hashable, one version
        # uses getcallargs to substitute default arguments correctly, the other
        # just provides a tuple of (args, kwargs) and is used as a backup
        if isfunction(func) or ismethod(func):
            self._make_hashable = self._mhashfunc
        else:
            self._make_hashable = self._mhashother

    def _mhashfunc(self, *args, **kwargs):
        """ Get the hashable version of the supplied arguments """
        callargs = getcallargs(self._wrapped_func, *args, **kwargs)
        if hasattr(self._wrapped_func, "__self__") and \
                self._wrapped_func.__self__ is not None:
            spec = getargspec(self._wrapped_func)
            # Stop it hashing the self argument, this is already unique
            del callargs[spec.args[0]]
        return self._hasher(callargs)

    def _mhashother(self, *args, **kwargs):
        return self._hasher((args, kwargs))

    def clear_cache(self):
        """ Clear the cache """
        self._cache.clear()

    def rm_from_cache(self, *args, **kwargs):
        """ Remove the corresponding value from the cache """
        try:
            del self._cache[self._make_hashable(*args, **kwargs)]
        except KeyError:
            pass

    @property
    def cache_enabled(self):
        return self._cache_enabled

    def enable_cache(self):
        self._cache_enabled = True

    def disable_cache(self):
        self._cache_enabled = False

    def __call__(self, *args, **kwargs):
        """ Call the actual function """
        if not self.cache_enabled:
            return self._wrapped_func(*args, **kwargs)
        key = self._make_hashable(*args, **kwargs)
        if key not in self._cache:
            self._cache[key] = self._wrapped_func(*args, **kwargs)
        return self._on_return(self._cache[key])

memofunc = make_decorator(MemoFunc)

class LockMemoFunc(MemoFunc):
    """ Used to memoize a bound function on a lockable class

        The bound function will lock its class before being called
    """
    def __init__(self, func, clear_on_unlock, **kwargs):
        """ Initialise the bound function

            :param clear_on_unlock: Parameter bound object's locked() method
        """
        super(LockMemoFunc, self).__init__(func, **kwargs)
        self._clear_on_unlock = clear_on_unlock

    def __call__(self, *args, **kwargs):
        """ Call the function """
        with self._wrapped_func.__self__.locked(self._clear_on_unlock):
            return super(LockMemoFunc, self).__call__(*args, **kwargs)

class MemoMethod(object):
    """ Memoizes a class' method """

    def __init__(self, func, cache_cls=dict, on_return=lambda x: x,
                 hasher=_to_hashable, locks=True, clear_on_unlock=None):
        """ Memoize a bound method

            As 'locks' defaults to True, if a class has a 'locked' function
            (i.e. is a MemoClass) then a MemoFunc will default to locking the
            class, but only if it can.

            :param func: The function to memoize
            :param cache_cls: The type to use for caching, defaults to dict
            :param on_return: 
                An additional function called on the return value. The main use
                case for this is to supply a copy function, for the case when
                you memoize a function that returns a mutable type (like a list)
                that is constructed on the fly and shouldn't be persistent
                between calls, defaults to a lambda that just returns the value
                unmodified.
            :param hasher:
                The function that should be used to make the arguments hashable.
                It will receive the callargs dictionary as an argument, defaults
                to _to_hashable
            :param locks:
                If True, and the bound object has a 'locked' function, then will
                use that as a context manager
            :param clear_on_unlock:
                If locks is used, the argument to the 'locked' function
        """
        self._wrapped_func = func
        self._cache_cls = cache_cls
        self._on_return = on_return
        self._hasher = hasher
        self._bound_methods = {}
        self._locks = locks
        self._clear_on_unlock = clear_on_unlock

    def __get__(self, obj, objtype=None):
        if obj is None:
            # Retrieving from the class itself, therefore return the method
            # memoizer
            return self
        if id(obj) not in self._bound_methods:
            # Use python's internal function binding to make everything play
            # nice
            func = MethodType(self._wrapped_func, obj)
            kwargs = {
                    'cache_cls' : self._cache_cls,
                    'on_return' : self._on_return,
                    'hasher'    : self._hasher}
            if self._locks and hasattr(obj, 'locked') and callable(obj.locked):
                self._bound_methods[id(obj)] = LockMemoFunc(
                        func,
                        clear_on_unlock=self._clear_on_unlock,
                        **kwargs)
            else:
                self._bound_methods[id(obj)] = MemoFunc(func, **kwargs)
        return self._bound_methods[id(obj)]

    def clear_cache(self, bound=None):
        """ Clear the cache

            :param bound:
                If not None, clear only the cache corresponding to that object,
                if bound is None, clear all caches
        """
        if bound is not None and bound in self._bound_methods:
            self._bound_methods[bound].clear_cache()
        else:
            for v in itervalues(self._bound_methods):
                v.clear_cache()

    def __call__(self, bound, *args, **kwargs):
        return self.__get__(bound)(*args, **kwargs)
memomethod = make_decorator(MemoMethod)

class MemoClsMethod(MemoMethod):
    """ Memoize a classmethod

        Memomethod/memofunc do not interact nicely with the classmethod
        decorator, so this should be used instead where a classmethod should be
        memoized
    """

    def __get__(self, obj, objtype=None):
        if objtype is None:
            objtype = type(obj)
        if objtype not in self._bound_methods:
            func = MethodType(self._wrapped_func, objtype)
            self._bound_methods[objtype] = memofunc(
                    func=func,
                    cache_cls = self._cache_cls,
                    on_return = self._on_return,
                    hasher = self._hasher)
        return self._bound_methods[objtype]
memoclsmethod = make_decorator(MemoClsMethod)
