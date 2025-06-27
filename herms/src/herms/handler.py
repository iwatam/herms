"""
提供者と使用者を動的に結びつける仕組みを提供します。

ある機能を提供する側が提供者となり、その機能を使う側が使用者となります。

使用者は、:func:use()デコレータを使って、メソッドを宣言します。このメソッドは、文字列で指定されたクラスの
提供者が:func:apply()を実行したときに実行されます。クラスの指定は文字列で行われるため、インポートの必要が
ありません。

提供者は、使用者になる可能性があるオブジェクトそれぞれに対して、:func:apply()を呼びます。
"""

import sys
from types import MethodType, ModuleType
from typing import Any, Callable, Type, TypeAlias, TypeVar

T = TypeVar("T")
HandlerFunc: TypeAlias = Callable[[T, Any], None]
HandlerFuncDecorator: TypeAlias = Callable[[HandlerFunc[T]], HandlerFunc[T]]

_functions: list[tuple[str, HandlerFunc[Any]]] = []
_table: dict[Type[object], dict[Type[object], HandlerFunc[Any]]] = {}


def _resolve_name(name: str, module: ModuleType | None = None)->Any:
    names=name.split(":")
    if len(names)!=2:
        raise ValueError(name+": Name must be in the format MODULE:CLASS.")
    module=sys.modules.get(names[0])
    if module is None:
        return None
    
    x = None
    for n in name[1].split("."):
        x = getattr(x or module, n, None)
        if x is None:
            return None
    return x


def _resolve():
    global _functions

    def _res(s: str, f: HandlerFunc[Any]) -> bool:
        provider = _resolve_name(s)
        if provider is None:
            return True
        else:
            user = _resolve_name(
                f.__qualname__.rsplit(".", 1)[0], sys.modules[f.__module__]
            )
            t = _table.get(provider, None)
            if t is None:
                t = {}
                _table[provider] = t
            t[user] = f
            return False

    _functions = list(filter(lambda x: _res(x[0], x[1]), _functions))


def use(name: str) -> HandlerFuncDecorator[Any]:
    """
    :func:apply()で実行されるメソッドを指定するデコレータです。

    名前には、提供側のクラスの名前を"モジュール:クラス名"の形式で書きます。
    """
    def deco(f: HandlerFunc[Any]):
        global _functions
        _functions.append((name, f))
        return f

    return deco


def apply(provider: object, user: object):
    """
    :func:use()でデコレートされたメソッドを呼び出します。

    引数には提供側と使用側を指定します。
    """
    _resolve()
    for provs in provider.__class__.__mro__:
        table = _table.get(provs, None)
        if table is not None:
            funcs = {}
            for users in user.__class__.__mro__:
                f = table.get(users, None)
                if f is not None and f.__name__ not in funcs:
                    funcs[f.__name__] = True
                    m = MethodType(f, user)
                    m(provider)
