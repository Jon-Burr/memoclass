from builtins import object
from .memoize import (
        memoclsmethod, memomethod, memofunc, MemoMethod,
        MemoClsMethod, make_decorator)
from functools import wraps
from contextlib import contextmanager
from future.utils import iteritems

def mutates(func, mutates_cls=False):
    """ Signal that a method mutates its class

        Here, mutates means that it clears the caches on any memomethods on the
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

class MemoClass(object):
    """ A class with several utilities to enable interacting with memoized
        methods

        A MemoClass' methods can be declared mutating, in which case they will
        automatically clear the caches on any memomethods present on it.

        Alternatively, a MemoClass can be locked, which prevents calling any
        mutating methods. By default, locking enables caching and unlocking
        disables and clears the caches *if they were disabled before*, which
        allows it to temporarily create a 'const' object. This is useful when an
        object has time consuming attributes to calculate but may change in ways
        that are difficult to reset the caches on (for example, if the class
        calculates values based on another object that it doesn't own or
        control).
    """

    def __init__(self, mutable_attrs=()):
        """ Create the object
            
            :param mutable_attrs:
                Any attributes to be treated as mutable. Setting a mutable
                attribute does not mutate the class and therefore is allowed on
                locked classes and will not reset the class' caches. If
                mutable_attrs is None then *all* attributes are treated as
                mutable
        """
        if mutable_attrs is not None:
            mutable_attrs = \
                    set(mutable_attrs) | set(("_locked", "_caches_enabled"))
        self._locked = False
        self.enable_caches()
        self._mutable_attrs = mutable_attrs

    @memoclsmethod
    def _memomethods(cls, base=True, clsmethods=False):
        """ List the memomethods associated with this class """
        if not base:
            return set(k for k, v in iteritems(cls.__dict__)
                if isinstance(v, MemoMethod) and
                (clsmethods or not isinstance(v, MemoClsMethod) ) )
        else:
            return set().union(*(
                    subcls._memomethods(False, clsmethods)
                    for subcls in cls.mro() if issubclass(subcls, MemoClass)))

    def enable_caches(self, clsmethods=False):
        """ Enable the cache on all memomethods """
        self._caches_enabled = True
        for m in self._memomethods(clsmethods=clsmethods):
            getattr(self, m).enable_cache()

    def disable_caches(self, clsmethods=False):
        """ Disable the cache on all memomethods """
        self._caches_enabled = False
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
        self.enable_caches()
        self._locked = True

    def unlock(self, clear_caches):
        """ Unlock the class

            :param clear_caches:
                If True, disable the class' caches and clear them
        """
        self._locked = False
        if clear_caches:
            self.disable_caches()
            self.clear_caches()

    @contextmanager
    def locked(self, clear_on_unlock=None):
        """ A context manager that temporarily locks the class

            Does nothing if the class is already locked
    
            :param clear_on_unlock:
                If True, disable the class' caches and clear them when
                unlocking. The caches will only be cleared if the class was
                unlocked before calling locked
        """
        if clear_on_unlock is None:
            # Clear and disable the caches when unlocking if they were disabled
            # before
            clear_on_unlock = not self._caches_enabled
        if self.is_locked:
            yield
        else:
            self.lock()
            yield
            self.unlock(clear_on_unlock)

    @contextmanager
    def unlocked(self, clear_caches=True):
        """ A context manager that temporarily unlocks the class
        
            Does nothing if the class is already unlocked

            :param clear_caches:
                If True, clear and disable the caches when unlocking
        """
        if self.is_locked:
            self.unlock(clear_caches)
            yield
            self.lock()
        else:
            yield

    def __setattr__(self, key, value):
        """ By default, setting an attribute on a class should mutate it """
        if key == "_locked" or \
           (hasattr(self, "_mutable_attrs") and (
               self._mutable_attrs is None or key in self._mutable_attrs) ):
            pass
        elif hasattr(self, "_locked") and self.is_locked:
            raise ValueError(
                    "Cannot set attribute {0} on locked class {1}".format(
                        key, self) )
        else:
            self.clear_caches()
        return super(MemoClass, self).__setattr__(key, value)
