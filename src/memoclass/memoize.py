""" Basic decoarators for memoizing functions and methods"""

from builtins import object
from functools import update_wrapper, partial
from inspect import getcallargs, isfunction, ismethod
from types import MethodType
from future.utils import iteritems, itervalues, PY3
if PY3:
    from collections.abc import MutableMapping
    from inspect import getfullargspec as getargspec
    from inspect import signature, Signature, Parameter
else:
    from collections import MutableMapping
    from inspect import getargspec
    from funcsigs import signature, Signature, Parameter
import weakref

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

def bind_callargs(sig, *args, **kwargs):
    """ Convert a set of args and kwargs into a dictionary of function arguments
        including defaults

        This is different to the result of signature.bind(*args,
        **kwargs).arguments as it includes defaults. It's different to
        inspect.getcallargs as it works properly on callables.
        It's equivalent to

        >>> b = sig.bind(*args, **kwargs)
        >>> b.apply_defaults()
        >>> return dict(b.arguments)

        but the apply_defaults function is python3 only and not included in
        funcsigs
    """
    bound = sig.bind(*args, **kwargs).arguments
    params = sig.parameters
    callargs = {}
    for name, parameter in iteritems(params):
        try:
            # Get the paramter value from the bound arguments
            callargs[name] = bound[name]
        except KeyError:
            # Have to get the 'default' value
            if parameter.default is not Signature.empty:
                # There *is* a default!
                callargs[name] = parameter.default
            elif parameter.kind == Parameter.VAR_POSITIONAL:
                # The default for varargs is an empty tuple
                callargs[name] = ()
            elif parameter.kind == Parameter.VAR_KEYWORD:
                # The default for varkwargs is an empty dict
                callargs[name] = {}
            else:
                # This *should* be impossible as if we reach here, bind should
                # have failed
                # Raise a TypeError, as that is what bind should have raised
                raise TypeError(
                        "Cannot find default value for parameter " + name)
    return callargs

def make_decorator(decorator):
    def inner(func=None, **kwargs):
        if func is None:
            return partial(decorator, **kwargs)
        else:
            return decorator(func, **kwargs)
    return inner

class MemoFunc(object):
    """ Memoizes a free function """
    def __init__(self, func, cache=None, on_return=lambda x: x,
                 prehash=_to_hashable):
        """ Memoize a free function

            :param func: The function to memoize
            :param cache:
                The cache to use, if None is provided, use an empty dict. This
                allows keeping hold of a cache without persisting the MemoFunc.
                The main use for this is when memoising a bound function we do
                not add an extra reference to the object that cannot be garbage
                collected.
            :param on_return: 
                An additional function called on the return value. The main use
                case for this is to supply a copy function, for the case when
                you memoize a function that returns a mutable type (like a list)
                that is constructed on the fly and shouldn't be persistent
                between calls, defaults to a lambda that just returns the value
                unmodified.
            :param prehash:
                The function that should be used to make the arguments hashable.
                It will receive the callargs dictionary as an argument
        """
        update_wrapper(self, func)
        # Set the __wrapped__ attribute to play nicely with signature
        self.__wrapped__ = func
        # Cache the signature here, rather than recalculating it every call
        self._signature = signature(func)
        self._cache = {} if cache is None else cache
        self._on_return = on_return
        self._prehash = prehash
        self._cache_enabled = True

    def clear_cache(self):
        """ Clear the cache """
        self._cache.clear()

    def rm_from_cache(self, *args, **kwargs):
        """ Remove the corresponding value from the cache """
        try:
            del self._cache[self._prehash(
                bind_callargs(self._signature, *args, **kwargs) )]
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
            return self.__wrapped__(*args, **kwargs)
        key = self._prehash(bind_callargs(self._signature, *args, **kwargs) )
        if key not in self._cache:
            self._cache[key] = self.__wrapped__(*args, **kwargs)
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
        with self.__wrapped__.__self__.locked(self._clear_on_unlock):
            return super(LockMemoFunc, self).__call__(*args, **kwargs)

class MemoMethod(object):
    """ Memoizes a class' method """

    def __init__(self, func, cache_cls=dict, on_return=lambda x: x,
                 prehash=_to_hashable, locks=True, clear_on_unlock=None):
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
            :param prehash:
                The function that should be used to make the arguments hashable.
                It will receive the callargs dictionary as an argument, defaults
                to _to_hashable
            :param locks:
                If True, and the bound object has a 'locked' function, then will
                use that as a context manager
            :param clear_on_unlock:
                If locks is used, the argument to the 'locked' function
        """
        self.__wrapped__ = func
        self._cache_cls = cache_cls
        self._on_return = on_return
        self._prehash = prehash
        self._bound_caches = {}
        self._weakrefs = []
        self._locks = locks
        self._clear_on_unlock = clear_on_unlock

    def __get__(self, obj, objtype=None):
        if obj is None:
            # Retrieving from the class itself, therefore return the method
            # memoizer
            return self
        obj_id = id(obj)
        if obj_id not in self._bound_caches:
            # Create a new cache
            cache = self._cache_cls()
            self._bound_caches[obj_id] = cache
            def _on_delete(r):
                self._weakrefs.remove(r)
                del self._bound_caches[obj_id]
            self._weakrefs.append(weakref.ref(obj, _on_delete) )
        else:
            cache = self._bound_caches[obj_id]
        func = MethodType(self.__wrapped__, obj)
        kwargs = {
                # Use python's internal function binding
                # 'func' : MethodType(self.__wrapped__, obj),
                'func' : func,
                'cache' : cache,
                'on_return' : self._on_return,
                'prehash' : self._prehash}
        # Pick the right type to use (i.e. use a LockMemoFunc if we should)
        if self._locks and hasattr(obj, 'locked') and callable(obj.locked):
            return LockMemoFunc(clear_on_unlock=self._clear_on_unlock, **kwargs)
        else:
            return MemoFunc(**kwargs)

    def clear_cache(self, bound=None):
        """ Clear the cache

            :param bound:
                If not None, clear only the cache corresponding to that object,
                if bound is None, remove all caches
        """
        if bound is None:
            self._bound_caches.clear()
            # Python2 doesn't have a list.clear method...
            del self._weakrefs[:]
        elif id(bound) in self._bound_caches:
            self._bound_caches[id(bound)].clear()

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
        if id(objtype) not in self._bound_caches:
            # create a new cache
            cache = self._cache_cls()
            self._bound_caches[id(objtype)] = cache
        else:
            cache = self._bound_caches[id(objtype)]
        return memofunc(
                func=MethodType(self.__wrapped__, objtype),
                cache=cache,
                on_return=self._on_return,
                prehash=self._prehash)
memoclsmethod = make_decorator(MemoClsMethod)
