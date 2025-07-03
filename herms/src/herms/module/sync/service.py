
from __future__ import annotations

import copy
import logging
from typing import Any, Iterable, Required, TypedDict, cast

from herms import Repository, Service,Node, Json, JsonSchema,RepositoryConfig,Query,Tag,NodeType,State

logger = logging.getLogger(__name__)


class SyncServiceConfig(TypedDict,total=False):
    target:Required[str|RepositoryConfig]
    condition:str

class SyncService(Service):
    CONFIG_SCHEMA={
        "type":"object",
        "properties":{
            "target":{
                "anyOf":[
                    {"type":"string"},
                    Repository.CONFIG_SCHEMA
                ]
            },
            "condition":{"type":"string"}
        },
        "required":["target"]
    }
    target:Repository
    condition:Query

    def node_config_schema(self) -> JsonSchema:
        return {"type":"object"}

    def __init__(self):
        super().__init__()

    def configure(self, data: Json) -> None:
        """設定を適用します。"""
        super().configure(data)
        cfg=cast(SyncServiceConfig,data)
        target=Repository()
        target.configure(cast(Json,cfg["target"]))
        self.target=target
        self.condition=Query(cfg.get("condition",""),self.owner)

    async def init(self):
        """
        初期化をします。

        起動時に1回呼ばれます。
        """
        await self.target.init()

    async def update(self, *nodes:Node,intensive:bool=False)->Iterable[Node]:
        modified:set[Node]=set()
        if not nodes:
            condition=self.owner.query(self.condition)
            newnodes:list[tuple[Node,Node]]=[]
            for node in self.target.nodes.iterate():
                if condition.match(node):
                    mynode=self.owner.node(node.name,node.type)
                    if mynode is None:
                        mynode=Node(self._import(node.type,None))
                        mynode.name=node.name
                        self.owner.nodes.add(mynode)
                        newnodes.append((node,mynode))
                    else:
                        if self._merge(node,mynode):
                            modified.add(node)
            for node,newnode in newnodes:
                self.clone(node,newnode)
            new_nodes=[x[1] for x in newnodes]
            self.owner.init_nodes(*new_nodes)
            modified.update(new_nodes)
        else:
            for node in nodes:
                remotenode=self._import(node,self.target)
                if self._merge(remotenode,node):
                    modified.add(node)
        return modified
    async def close(self):
        await self.target.close()
        await super().close()

    def _merge(self,remote:Node,local:Node):
        pass

    def _import(self,obj:Any,repo:Repository|None)->Any:
        if repo is None:
            repo=self.owner
        if isinstance(obj,Tag):
            tag=obj
            parent=tag.parent
            if parent is not None:
                parent=self._import(parent,repo)
            return repo.tag_or_create(tag.absname(),parent)
        elif isinstance(obj,NodeType):
            return repo.types[obj.name]
        elif isinstance(obj,Node):
            return repo.nodes[self._import(obj.type,repo)][obj.name]
        elif isinstance(obj,Service):
            return repo.services[obj.name]
        elif isinstance(obj,State):
            return repo.states[obj.name]
        elif isinstance(obj,list):
            return [self._import(x,repo) for x in cast(list[Any],obj)]
        elif isinstance(obj,dict):
            return {self._import(k,repo):self._import(x,repo) for k,x in cast(dict[Any,Any],obj).items()}
        else:
            return copy.deepcopy(obj)

    def clone(self,src:Node,dest:Node):
        repo=dest.owner
        dest.description=src.description
        dest.state=self._import(src.state,repo)
        dest.tags=[self._import(t,repo) for t in src.tags]
        service_configs={}
        for service,config in src.service_configs.items():
            myservice=repo.services.get(service.name)
            if myservice is not None:
                service_configs[myservice]=self._import(config,repo)
        dest.service_configs=service_configs
        dest.properties=self._import(src.properties,repo)
        dest.properties_rev=self._import(src.properties_rev,repo)

