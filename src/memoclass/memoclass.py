from builtins import object
from .memoize import memoclsmethod, memomethod, memofunc
from functools import wraps
from contextlib import contextmanager
from future.utils import iteritems

def mutating(func, mutates_cls=False):
    """ Signal that a method mutates its class

        Here, mutating means that it clears the caches on any memomethods on the
        class calling the method

        :param mutates_cls:
            If True, any class methods also have their caches cleared
    """
    @wraps(func)
    def inner(self, *args, **kwargs):
        if self.is_locked:
            raise ValueError(
                    "Cannot call mutating method {0} on locked class {1}".format(
                        func.__name__, self) )
        self.clear_caches(clsmethods=mutates_cls)
        return func(self, *args, **kwargs)
    return inner

class lockmemofunc(memofunc):
    """ A modified memofunc that locks the class it's called on while the method
        is being called
    
        This can only be added to a bound method on a MemoClass
    """
    def __init__(self, *args, clear_on_unlock=True, **kwargs):
        super(lockmemofunc, self).__init__(*args, **kwargs)
        self._clear_on_unlock=clear_on_unlock

    def __call__(self, *args, **kwargs):
        with self._wrapped_func.__self__.locked(self._clear_on_unlock):
            return super(lockmemofunc, self).__call__(*args, **kwargs)

class lockmemomethod(memomethod):
    """ A modified memomethod that locks the class it's called on while the
        method is being called

        This can only be added to a bound method on a MemoClass
    """
    def __init__(self, *args, **kwargs):
        super(lockmemomethod, self).__init__(
                *args, memofunc_cls=lockmemofunc, **kwargs)

class MemoClass(object):
    """ A class with several utilities to enable interacting with memoized
        methods

        A MemoClass' methods can be declared mutating, in which case they will
        automatically clear the caches on any memomethods present on it.

        Alternatively, a MemoClass can be locked, which prevents calling any
        mutating methods. By default, locking enables caching and unlocking
        disables and clears the caches, which allows it to temporarily create a
        'const' object. This is useful when an object has time consuming
        attributes to calculate but may change in ways that are difficult to
        reset the caches on (for example, if the class calculates values based
        on another object that it doesn't own or control).
    """

    def __init__(self, mutable_attrs=None, attrs_mutate_base=True):
        if mutable_attrs is None:
            mutable_attrs = set()
        self._locked = False
        self._attrs_mutate_base = attrs_mutate_base
        self._mutable_attrs = mutable_attrs

    @memoclsmethod
    def _memomethods(cls, base=True, clsmethods=False):
        """ List the memomethods associated with this class """
        if not base:
            return set(k for k, v in iteritems(cls.__dict__)
                if isinstance(v, memomethod) and
                (include_clsmethods or not isinstance(memoclsmethod) ) )
        else:
            return set().union(
                    subcls._memomethods(False, clsmethods)
                    for subcls in cls.mro() )

    def enable_caches(self, clsmethods=False):
        """ Enable the cache on all memomethods """
        for m in self._memomethods(clsmethods=clsmethods):
            getattr(self, m).enable_cache()

    def disable_caches(self, clsmethods=False):
        """ Disable the cache on all memomethods """
        for m in self._memomethods(clsmethods=clsmethods):
            getattr(self, m).disable_cache()

    def clear_caches(self, clsmethods=False):
        """ Clear the cache on all memomethods """
        for m in self._memomethods(clsmethods=clsmethods):
            getattr(self, m).clear_cache()

    @property
    def is_locked(self):
        """ Is this class locked """
        return self._locked

    def lock(self):
        """ Lock the class
        
            A locked class' caches are always enabled and calling a mutating
            method on it results in a ValueError
        """
        self._locked = True
        self.enable_caches()

    def unlock(self, clear_caches=True):
        """ Unlock the class

            :param clear_caches:
                If True, disable the class' caches and clear them
        """
        self._locked = False
        if clear_caches:
            self.disable_caches()
            self.clear_caches()

    @contextmanager
    def locked(self, clear_on_unlock=True):
        """ A context manager that temporarily locks the class

            :param clear_on_unlock:
                If True, disable the class' caches and clear them when
                unlocking. The caches will only be cleared if the class was
                unlocked before calling locked
        """
        was_locked = self.is_locked
        if not was_locked:
            self.lock()
        yield
        if not was_locked:
            self.unlock(clear_on_unlock)

    @contextmanager
    def unlocked(self, clear_caches=True):
        """ A context manager that temporarily unlocks the class """
        self.clear_caches()
        self.disable_caches()
        was_locked = self.is_locked
        if was_locked:
            self.unlock()
        yield
        self.enable_caches()
        if was_locked:
            self.lock()

    def __setattr__(self, key, value):
        """ By default, setting an attribute on a class should mutate it """
        if hasattr(self, "_mutable_attrs") and key in self._mutable_attrs:
            pass
        elif self.is_locked:
            raise ValueError(
                    "Cannot set attribute {0} on locked class {1}".format(
                        key, self) )
        else:
            self.clear_caches(self._attrs_mutate_base)
        return super(MemoClass, self).__setattr__(key, value)
