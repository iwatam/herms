from __future__ import annotations
#
# Data Type
#

from typing import TYPE_CHECKING, Any, cast
from .config import Json, JsonSchema

JSON_DATA_TYPE=['string','number','integer','boolean']
DATA_TYPE_ALIAS={
    'str':'string',
    'float':'number',
    'int':'integer',
    'bool':'boolean'
}
type DataType = str | Tag | NodeType | None

class DataTypeConverter:
    def encode(self,val:Any,type:DataType)->Json:
        return val
    def decode(self,text:Json,type:DataType,repo:Repository,create:bool)->Any:
        return text
DATA_TYPE_CONVERTER_DEFAULT=DataTypeConverter()

def schema_of(type:DataType)->JsonSchema:
    if type is None:
        return {}
    elif isinstance(type,str):
        if type in JSON_DATA_TYPE:
            typename=type
        elif type in DATA_TYPE_ALIAS:
            typename=DATA_TYPE_ALIAS[type]
        elif type in DATA_TYPE_CONVERTER:
            typename="string"
        else:
            typename=type
        return {"type":typename}
    else:
        return {"type":"string"}

def to_type(name:str,repo:Repository)->DataType:
    if name in repo.types:
        return repo.types[name]
    tag=repo.tag(name)
    if tag is not None:
        return tag
    return name

#
# further implementation
#
from .nodetype import NodeType
from .node import Node
from .tag import Tag
if TYPE_CHECKING:
    from .repository import Repository

class _StringConverter(DataTypeConverter):
    pass
class _NumberConverter(DataTypeConverter):
    def decode(self,text:Json,type:DataType,repo:Repository,create:bool)->Any:
        if isinstance(text,float):
            return text
        else:
            return float(cast(str,text))
class _IntegerConverter(DataTypeConverter):
    def decode(self,text:Json,type:DataType,repo:Repository,create:bool)->Any:
        if isinstance(text,int):
            return text
        else:
            return int(cast(str,text))
class _BooleanConverter(DataTypeConverter):
    def decode(self,text:Json,type:DataType,repo:Repository,create:bool)->Any:
        if isinstance(text,bool):
            return text
        else:
            return cast(str,text).lower() in ['1','true','yes']
class _TagConverter(DataTypeConverter):
    def encode(self,val:Any,type:DataType)->Json:
        tag=cast(Tag,val)
        return tag.name if tag.parent==type else tag.absname()
        
    def decode(self,text:Json,type:DataType,repo:Repository,create:bool)->Any:
        return repo.tag(cast(str,text))
class _NodeConverter(DataTypeConverter):
    type:NodeType|None
    def __init__(self,type:NodeType|None=None):
        self.type=type
    def encode(self,val:Any,type:DataType)->Json:
        node=cast(Node,val)
        if self.type==None or self.type!=node.type:
            return node.type.name+":"+node.name
        else:
            return node.name
        
    def decode(self,text:Json,type:DataType,repo:Repository,create:bool)->Any:
        return repo.node(cast(str,text),self.type)


DATA_TYPE_CONVERTER:dict[str,DataTypeConverter]={
    "string":_StringConverter(),
    "number":_NumberConverter(),
    "integer":_IntegerConverter(),
    "boolean":_BooleanConverter(),
    "tag":_TagConverter(),
    "node":_NodeConverter()
}

def _converter_of(type:DataType)->DataTypeConverter:
    if isinstance(type,NodeType):
        return _NodeConverter(type)
    t:str
    if type is None:
        return DATA_TYPE_CONVERTER_DEFAULT
    elif isinstance(type,Tag):
        t="tag"
    else:
        t=type
    t=DATA_TYPE_ALIAS.get(t,t)
    return DATA_TYPE_CONVERTER[t]

def is_node(type:DataType)->bool:
    return type=='node' or isinstance(type,NodeType)

def is_tag(type:DataType)->bool:
    return type=='tag' or isinstance(type,Tag)

def decode(data:Json,type:DataType,repo:Repository,create:bool=False)->Any:
    return _converter_of(type).decode(data,type,repo,create)

def encode(val:Any,type:DataType,repo:Repository)->Json:
    return _converter_of(type).encode(type,val)
def register(name:str,conv:DataTypeConverter):
    DATA_TYPE_CONVERTER[name]=conv