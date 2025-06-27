
from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, ClassVar, TypedDict, cast

from .datatype import DataType, schema_of, to_type
from .base import InRepository, OwnedBy, OwnedDict
from .tag import Tag

if TYPE_CHECKING:
    from .config import Json, JsonSchema

class PropertyConfig(TypedDict,total=False):
    type:str|JsonSchema
    required:bool
    list:bool
    default:Any

class Property(OwnedBy["NodeType"]):
    parent: NodeType
    name: str
    type: DataType
    required: bool
    list: bool
    default: Any = None

    #
    # Accessors
    #
    def is_node(self):
        return self.type=="node" or isinstance(self.type,NodeType)
    def is_tag(self):
        return self.type=="tag" or isinstance(self.type,Tag)

    def validate(self, value: Any) -> Any:
        # TODO
        return value

    def __hash__(self):
        return hash(str(self.name))
    
    def schema(self)->JsonSchema:
        type:JsonSchema=schema_of(self.type)
        if self.list:
            type={"type":"array","items":type}
        return type
    
    def serialize(self,value:Any)->Json:
        if self.list:
            return [self.serialize_item(x) for x in value]
        else:
            return self.serialize_item(value)

    def serialize_item(self,value:Any)->Json:
        if isinstance(self.type,Tag):
            pass
        elif isinstance(self.type,NodeType):
            pass
        elif isinstance(self.type,str):
            pass
        else:
            return value

    def deserialize(self,value:Json)->Any:
        if self.list:
            return [self.deserialize_item(x) for x in cast(list[Json],value)]
        else:
            return self.deserialize_item(value)
    def deserialize_item(self,value:Json)->Any:
        pass

class NodeTypeConfig(TypedDict,total=False):
    base:str
    properties:dict[str,str|PropertyConfig]

class NodeType(InRepository):
    #
    # Schema
    #
    CONFIG_SCHEMA:ClassVar[JsonSchema]={
        "type":"object",
        "properties":{
            "base":{"type":"string"},
            "properties":{
                "type":"object",
                "additionalProperties":{
                    "anyOf":[
                    {"type":"string"},
                    {"type":"object",
                     "properties":{
                         "type":{},
                         "required":{"type":"boolean"},
                         "list":{"type":"boolean"},
                         "default":{}
                     }},
                ]}
            }
        }
    }
    def node_config_schema(self)->JsonSchema:
        props:Json={p.name:p.schema() for p in self.properties.values()}
        services:Json={s.name:s.node_config_schema() for s in self.owner.services.values()}
        required:list[Json]=[x.name for x in self.properties.values() if x.required]
        return {
            "type":"object",
            "properties":{
                "props":props,
                "services":services
            },
            "required":required
        }
    #
    # Properties
    #
    base: NodeType | None = None
    properties: OwnedDict[Property,NodeType]
    
    #
    # Accessor
    #
    def ancestors(self)->Iterable[NodeType]:
        t=self
        while True:
            yield t
            t=self.base
            if t is None:
                break


    #
    # Initialization and configuration
    #
    def __init__(self):
        self.properties = OwnedDict(self)

    def configure(self, data: Json) -> None:
        """ノードタイプを設定します。"""
        if data is None:
            data={}
        config:NodeTypeConfig=cast(NodeTypeConfig,data)
        if "base" in config:
            base=config["base"]
            assert isinstance(base,str)
            self.base = self.owner.types[base]
        else:
            self.base=None
        for name, cfg in config.get("properties",{}).items():
            type:Any=None
            required:bool=False
            list:bool=False
            default=None
            if isinstance(cfg, str):
                type = cfg
            else:
                type = to_type(cfg.get("type", type),self.owner)
                required = cfg.get("required", required)
                default=cfg.get("default",default)
                list=cfg.get("list",list)
            prop = Property()
            prop.name = name
            prop.type = type
            prop.required = required
            prop.list=list
            prop.default=default
            self.properties[name] = prop
