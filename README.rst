=========
memoclass
=========
-----------------------------------------------------------
A utility package for memoizing functions and class methods
-----------------------------------------------------------

Memoization_ is a common technique used primarily as an optimizer, allowing the
caching of the return values of expensive functions. When a memoized function is
called with a given set of arguments for the first time its return value is
cached, and that value is then returned on all subsequent calls.

While many memoization packages exist, as well as instructions to write your own
simple decorator, this package provides enhanced utility for memoizing methods
on *classes*. Especially, this allows for a couple of ways of automatically
clearing the caches related to a particular instance, for example, when changing
a member variable would change the result of those functions. This package also
uses ``inspect.getcallargs`` to correctly treat default argument values, where
possible.

.. _Memoization: https://en.wikipedia.org/wiki/Memoization
