from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Iterator, TypedDict

from .config import JsonSchema
from .base import InRepository

if TYPE_CHECKING:
    from .query import Query
    from .repository import Repository

type TagConfig=list[str] | dict[str,str | _TagConfig]

class _TagConfig(TypedDict,total=False):
    abstract: bool
    description:str
    expression:str
    children:TagConfig

class Tag(InRepository):
    CONFIG_SCHEMA:JsonSchema={
        "type":"object",
        "properties":{
            "abstract":{"type":"boolean"},
            "description":{"type":"string"},
            "expression":{"type":"string"},
            "children":{"type":"object"}
        }
    }

    index: int = 0
    abstract: bool = False
    expression: str | None = None
    _query:Query|None=None
    parent: Tag | None = None
    children: dict[str, Tag]

    def __init__(self):
        self.children = {}

    def __str__(self) -> str:
        if self.parent is not None:
            return str(self.parent) + "." + self.name
        else:
            return self.name

    def absname(self)->str:
        if self.parent is None:
            return self.name
        else:
            return self.parent.absname()+"."+self.name

    def match(self, names: str | list[str]) -> bool:
        """名前が一致するかどうかを判定します。"""
        if isinstance(names, str):
            names = names.split(".")
        i = len(names) - 1
        if names[i] != self.name:
            return False
        i -= 1
        while (p := self.parent) is not None:
            if p.name == names[i]:
                if i == 0:
                    return True
                else:
                    i -= 1
        return False

    def walk(self) -> Iterator[Tag]:
        yield self
        for x in self.children.values():
            yield from x.walk()

    def isa(self, val: Tag) -> bool:
        t: Tag|None = self
        while t is not None:
            if t == val:
                return True
            t = t.parent
        return False
    
    def assign(self, owner: Repository, name: str):
        super().assign(owner,name)
        if self.expression is not None:
            self._query=Query(self.expression,owner)

    @staticmethod
    def configure(config: TagConfig|None) -> Iterable[Tag]:
        """TagConfigをもとに、Tagを作成します。"""

        if config is None:
            return
        conf:dict[str,str|_TagConfig]
        if isinstance(config, list):
            conf = {name: {} for name in config}
        else:
            conf=config
        for name,val in conf.items():
            cfg:_TagConfig
            if isinstance(val,str):
                cfg={"description":val}
            else:
                cfg=val
            tag = Tag()
            tag.name = name
            tag.abstract = cfg.get("abstract",False)
            tag.description = cfg.get("description","")
            tag.parent=None
            query=cfg.get("expression",None)
            if query is None:
                tag.expression=None
            else:
                tag.expression = query
            if "children" in cfg:
                for child in Tag.configure(cfg["children"]):
                    child.parent=tag
                    tag.children[child.name]=child
            yield tag
