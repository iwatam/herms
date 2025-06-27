from __future__ import annotations
from typing import TYPE_CHECKING, Generic, TypeVar, cast

if TYPE_CHECKING:
    from .repository import Repository

OWNER=TypeVar("OWNER")

class OwnedBy(Generic[OWNER]):
    name: str
    description: str = ""
    owner:OWNER

    def assign(self, owner: OWNER, name: str):
        self.owner = owner
        self.name = name

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other:object):
        return str(self) == str(other)

    def __str__(self):
        return self.name

class InRepository(OwnedBy["Repository"]):
    pass

T=TypeVar("T")
class OwnedDict(dict[str,T],Generic[T,OWNER]):
    def __init__(self,owner:OWNER):
        super().__init__()
        self.owner=owner

    def __setitem__(self, key:str, value:T):
            super().__setitem__(key, value)
            obj=cast(OwnedBy[OWNER],value)
            obj.assign(self.owner,key)
