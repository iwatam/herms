from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any, NotRequired, TypedDict, cast
import jsonschema

from . import datatype,util
from .tag import Tag
from .config import JsonObject
from .base import InRepository
from .nodetype import NodeType,Property

if TYPE_CHECKING:
    from .service import Service
    from .state import State

class NodeConfig(TypedDict):
    state:str
    properties:NotRequired[dict[str,Any]]
    services:NotRequired[dict[str,Any]]
    tags:NotRequired[list[str]]

class Node(InRepository):
    CONFIG_SCHEMA:dict[str,Any]={
        "type":"object",
        "properties":{
            "state":{"type":"string"},
            "properties":{"type":"object"},
            "services":{"type":"object"},
            "tags":{"type":"string"}
        },
        "required":["state"]
    }
    type: NodeType
    """ノードの種類"""

    state:State

    properties: dict[Property, Any]
    """ノードのプロパティ"""
    properties_rev:dict[Property,set[Node]]
    tags:list[Tag]
    service_configs: dict[Service, Any]

    def __init__(self, type: NodeType):
        self.type = type
        self.properties = {}
        self.properties_rev = defaultdict(set)
        self.service_configs = {}
        self.tags=[]

    def configure(self, data: JsonObject) -> None:
        """ノードを設定します。"""
        config=cast(NodeConfig,data)
        self.state=self.owner.states[config["state"]]
        tags=config.get("tags",[])
        self.tags.clear()
        for name in tags:
            tag=self.owner.tag_or_create(name,None)
            self.tags.append(tag)
        props=config.get("properties",{})
        for name, prop in self.type.properties.items():
            cfg = props.get(name, None)
            if prop.list:
                if cfg is None:
                    val=[]
                else:
                    val=[datatype.decode(x,prop.type,self.owner,True) for x in cfg]
            else:
                val=datatype.decode(cfg,prop.type,self.owner,True)
            self.set_prop(prop,prop.validate(val))

        service_configs=config.get("services",{})
        for name, service in self.owner.services.items():
            cfg = service_configs.get(name, {})
            self.service_configs[service] = jsonschema.validate(cfg,service.node_config_schema())

    def set_prop(self,prop:Property,val:Any)->None:
        if prop.is_node():
            if prop.list:
                oldnodes=cast(list[Node],self.properties.get(prop,[]))
                nodes=cast(list[Node],val)
                util.modify_list(oldnodes,nodes,
                                 lambda x:x.properties_rev[prop].remove(self),
                                 lambda x:x.properties_rev[prop].add(self))
            else:
                oldnode=cast(Node|None,self.properties.get(prop))
                node=cast(Node,val)
                if oldnode is not None:
                    oldnode.properties_rev[prop].remove(self)
                self.properties[prop]=node
                node.properties_rev[prop].add(self)
        elif prop.is_tag():
            if prop.list:
                oldval=cast(list[Tag],self.properties.get(prop,[]))
                newval=cast(list[Tag],val)
                util.modify_list(oldval,newval,
                                 lambda x:self.tags.remove(x),
                                 lambda x:self.tags.append(x))
            else:
                oldval=cast(Tag|None,self.properties.get(prop))
                newval=cast(Tag,val)
                if oldval is not None:
                    self.tags.remove(oldval)
                self.properties[prop]=newval
                self.tags.append(newval)
        else:
            self.properties[prop]=val
