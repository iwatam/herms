from __future__ import annotations

import herms.base as t

class Parent:
    pass

class Child(t.OwnedBy[Parent]):
    pass

def test_owneddict():
    p=Parent()
    dic=t.OwnedDict[Child,Parent](p)
    c1=Child()
    dic["c1"]=c1
    c2=Child()
    dic["c2"]=c2

    assert c1.name=="c1"
    assert c2.name=="c2"
    assert c1.owner==p
    assert c2.owner==p
    assert dic["c1"]==c1
    assert dic["c2"]==c2

    