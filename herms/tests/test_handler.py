import sys
from typing import Callable

import herms.handler as t


class Prov1:
    pass


class Prov2:
    pass


class ProvC1(Prov1):
    pass


class User1:
    val: int = 0

    @t.use(__name__ + ".Prov1")
    def prov1(self, prov):
        self.val += 1


class User2:
    val: int = 0

    @t.use(__name__ + ".Prov3")
    def prov3(self, prov):
        self.val += 1


class User3(User1):
    @t.use(__name__ + ".Prov1")
    def prov1(self, prov):
        super().prov1(prov)
        self.val += 1


class User4(User1):
    @t.use(__name__ + ".Prov1")
    def prov1(self, prov):
        self.val += 1


class User5(User1):
    @t.use(__name__ + ".Prov1")
    def prov2(self, prov):
        self.val += 10


def test_resolve():
    assert sys.modules[__name__]
    assert t._resolve_name("FOOBAR") is None
    assert t._resolve_name("sys.modules") is not None
    assert t._resolve_name("sys.foobar") is None
    assert t._resolve_name("modules", sys.modules["sys"]) is not None
    assert t._resolve_name("User1", sys.modules[__name__]) == User1


def test_apply():
    assert len(t._functions) == 5

    u = User1()
    p = Prov1()
    t.apply(p, u)
    assert u.val == 1

    u = User2()
    t.apply(p, u)
    assert u.val == 0

    u = User3()
    t.apply(p, u)
    assert u.val == 2

    u = User4()
    t.apply(p, u)
    assert u.val == 1

    u = User5()
    t.apply(p, u)
    assert u.val == 11

    assert len(t._functions) == 1
