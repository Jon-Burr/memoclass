=========
memoclass
=========
-----------------------------------------------------------
A utility package for memoizing functions and class methods
-----------------------------------------------------------

.. role:: python(code)
    :language: python

.. image:: https://github.com/Jon-Burr/memoclass/workflows/PyTest/badge.svg

Introduction
============

Memoization_ is a common technique used primarily as an optimizer, allowing the
caching of the return values of expensive functions. When a memoized function is
called with a given set of arguments for the first time its return value is
cached, and that value is then returned on all subsequent calls.

While many memoization packages exist, as well as instructions to write your own
simple decorator, this package provides enhanced utility for memoizing methods
on *classes*. Especially, this allows for a couple of ways of automatically
clearing the caches related to a particular instance, for example, when changing
a member variable would change the result of those functions. This package also
uses :python:`inspect.signature` to correctly treat default argument values, where
possible.

Preliminary sphinx documentation can be found at
https://jon-burr.github.io/memoclass/memoclass.html

The project is hosted on github at https://github.com/Jon-Burr/memoclass

Installation
============

.. code:: bash

  pip install memoclass

Overview of core components
===========================

:python:`memoclass.memoize.memofunc`
------------------------------------

Memoizes a single free function. The returned object is a :python:`MemoFunc` object,
which has functions that allow you to temporarily disable the caching, or clear
it entirely.

.. code:: python

  >>> from memoclass.memoize import memofunc
  >>>
  >>> @memofunc
  >>> def build_list(x):
  >>>     return [1, 2, 3, x]
  >>> 
  >>> a = build_list(5)
  >>> b = build_list(5)
  >>> a is b
  True
  >>> build_list.clear_cache()
  >>> c = build_list(5)
  >>> a is c
  False

The :python:`MemoFunc` class also has some extra properties that can be set while
decorating

.. code:: python

  >>> from memoclass.memoize import memofunc
  >>> import copy
  >>>
  >>> @memofunc(on_return=copy.copy)
  >>> def build_list(x):
  >>>     return [1, 2, 3, x]
  >>> 
  >>> a = build_list(5)
  >>> b = build_list(5)
  >>> a is b
  False

:python:`memoclass.memoize.memomethod`
--------------------------------------

Memoizes a class method. Methods bound to different instances have independent
caches, so the cache on one object can be cleared without clearing it for all
other objects.

.. code:: python

  >>> from memoclass.memoize import memomethod
  >>>
  >>> class ListBuilder(object):
  >>>     @memomethod
  >>>     def __call__(self, x):
  >>>         return [1, 2, 3, x]
  >>>
  >>> x = ListBuilder()
  >>> y = ListBuilder()
  >>> a = x()
  >>> b = y()
  >>> a is b
  False
  >>> x.__call__.clear_cache()
  >>> c = y()
  >>> b is c # Clearing x's cache has not touched y's
  True

:python:`memoclass.memoclass.MemoClass`
---------------------------------------

Base class meant to make interacting with memoized methods easier. It can
enabled, disable and clear all memomethods attached to an instance (note that
which methods exist is calculated at the *class* level, so any added onto an
instance will not be seen).

By default, setting any attribute will reset the object's caches, unless that
attribute has been provided to the :python:`mutable_attrs` argument of
:python:`MemoClass.__init__`. This behaviour can be disabled by setting
:python:`mutable_attrs=None`. Additionally, any function can have the
:python:`memoclass.memoclass.mutates` decorator applied to it, which will then reset
the caches whenever it is called.

.. code:: python

  >>> from memoclass.memoize import memomethod
  >>> from memoclass.memoclass import MemoClass
  >>>
  >>> class PartialSum(MemoClass):
  >>>
  >>>     def __init__(self, stored):
  >>>         super().__init__()
  >>>         self.stored = stored
  >>>
  >>>     @memomethod
  >>>     def __call__(self, other):
  >>>         return self.stored + other
  >>>
  >>> a = PartialSum(5)
  >>> a(3)
  8
  >>> a.stored = 3 # Triggers a cache reset
  >>> a(3)
  6

A :python:`MemoClass` can be ``locked`` which means that all caches are enabled and
calling a function marked :python:`mutates` or setting a non-mutable attribute results
in a :python:`ValueError`. When the class is then unlocked again, if the caches
were previously disabled, they will be disabled and cleared. This means it is
possible to create a class whose methods are only temporarily memoized. This
might be useful if a class has expensive methods to calculate that rely on a
global state. Note that by default, a :python:`memomethod` declared on a
:python:`MemoClass` will lock its caller while it is called.

.. _Memoization: https://en.wikipedia.org/wiki/Memoization
