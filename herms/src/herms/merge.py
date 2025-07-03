from typing import Callable, TypeVar


T=TypeVar("T")
def modify_list(oldlist:list[T],newlist:list[T],remove:Callable[[T],None],add:Callable[[T],None]):
    """
    oldlistがnewlistの内容になるよう、要素を追加・削除します。

    値はhashableでなくてはなりません。Nodeなどのherms内部クラスはhashableですが、名前のみで比較されるため、注意が必要です。
    要素の追加・削除のためにremove, addで指定した関数が呼ばれます。
    """
    oldset=set(oldlist)
    newset=set(newlist)
    for x in oldset-newset:
        remove(x)
    for x in newset-oldset:
        add(x)

K=TypeVar("K")
def modify_dict(olddict:dict[K,T],newdict:dict[K,T],remove:Callable[[K,T],None],add:Callable[[K,T],None]):
    oldset=set(olddict.keys())
    newset=set(newdict.keys())
    for x in oldset-newset:
        remove(x,olddict[x])
    for x in newset-oldset:
        add(x,newdict[x])
