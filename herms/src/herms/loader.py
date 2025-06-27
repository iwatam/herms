# -*- coding: utf-8 -*-
"""モジュールをロードする機構を提供します。

メインとなる関数は:func:`find_class`で、この関数を使って名前からクラスを取り出します。

:func:`add_loadpath` を使って、モジュールの格納先パスを登録します。


load() では、登録された Loader を順に使って、指定された名前のモジュールをロードします。

また、Python の import でもロードすることができます。
"""

import importlib
from pathlib import Path
import pkgutil
from typing import Type, TypeVar


def add_loadpath(path:Path):
    pass  # TODO: no custom moduledir support


def load_module(name:str):
    return importlib.import_module(name)


# TODO: support only default class
T=TypeVar("T",bound=object)

def find_class_or_default(name:str, classtype:Type[T])->Type[T]|None:
    try:
        ret = pkgutil.resolve_name(name)
        return ret
    except ModuleNotFoundError:
        return None
    except AttributeError:
        return None

def find_class(name:str, classtype:Type[T])->Type[T]:
    ret = pkgutil.resolve_name(name)
    return ret
