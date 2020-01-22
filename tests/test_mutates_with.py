""" Tests for the 'mutates with' approach """

from memoclass.memoize import memomethod
from memoclass.memoclass import MemoClass

class Provider(MemoClass):
    def __init__(self, value):
        self.receiver = None
        self.value = value
        super(Provider, self).__init__()

    def mutates_with_this(self):
        if self.receiver is None:
            return ()
        else:
            return (self.receiver,)

class Receiver(MemoClass):
    def __init__(self, provider):
        self.provider = provider
        super(Receiver, self).__init__()

    @memomethod
    def append(self, value):
        return self.provider.value + value

def test_cls():
    """ Make sure the classes work at all """
    p = Provider([1, 2, 3])
    r = Receiver(p)
    p.receiver = r
    assert r.append([4, 5]) == [1, 2, 3, 4, 5]

def test_no_receiver():
    """ Test what happens when the receiver is set (should result in incorrect
        behaviour)
    """
    p = Provider([1, 2, 3])
    r = Receiver(p)
    r.append([4, 5])
    p.value = [2, 3]
    # This is the wrong value now - changing p.value has *not* changed r.append
    assert r.append([4, 5]) == [1, 2, 3, 4, 5]

def test_receiver():
    """ Make sure that the provider mutates the receiver correctly """
    p = Provider([1, 2, 3])
    r = Receiver(p)
    p.receiver = r
    r.append([4, 5])
    p.value = [2, 3]
    assert r.append([4, 5]) == [2, 3, 4, 5]
