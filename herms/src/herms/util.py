from typing import Callable, TypeVar


T=TypeVar("T")
def modify_list(oldlist:list[T],newlist:list[T],remove:Callable[[T],None],add:Callable[[T],None]):
    oldset=set(oldlist)
    newset=set(newlist)
    for x in oldset-newset:
        remove(x)
    for x in newset-oldset:
        add(x)