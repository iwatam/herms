from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol, TypedDict, cast



from .base import OwnedDict


from .config import Json, JsonObject, JsonSchema, config_file_of, is_config_file, load_config_file, load_object, load_object_static
from .node import Node
from .nodetype import NodeType
from .service import Service
from .tag import Tag, TagConfig
from .query import Executor, Query, QuerySelector
from .repository_query import AllExecutor, AndExecutor, RepositoryQueryInterface
from .state import State

class RepositoryConfig(TypedDict,total=False):
    config_path:str
    data_path:str
    path:str
    node_path:str|dict[str,str]
    service_path:str|dict[str,str]
    nodes:dict[str,Json]
    tags:TagConfig
    types:dict[str,Json]
    services:dict[str,str|JsonObject]
    states:dict[str,Json]


class Repository:
    """
    データの集積場です。
    """

    CONFIG_SCHEMA:JsonSchema={
        "config_path":{"type":"string"},
        "data_path":{"type":"string"},
        "path":{"type":"string"},
        "node_path":{"anyOf":[
            {"type":"string"},
            {"type":"object",
             "additionalProperties":{"type":"string"}}
        ]},
        "service_path":{"anyOf":[
            {"type":"string"},
            {"type":"object",
             "additionalProperties":{"type":"string"}}
        ]},

        "node_service_path":{"type":"string"},
        "nodes":{
            "type":"object",
            "additionalProperties": Node.CONFIG_SCHEMA
        },
        "types":{
            "type":"object",
            "additionalProperties": NodeType.CONFIG_SCHEMA
        },
        "services":{
            "type":[
                {"type":"array","items":{"type":"string"}},
                {"type":"object",
                "additionalProperties": Service.CONFIG_SCHEMA
                }
            ],
        },
        "tags":{
            "type":"object",
            "additionalProperties": Tag.CONFIG_SCHEMA
        },
        "states":{
            "type":"object",
            "additionalProperties": State.CONFIG_SCHEMA
        }
    }

    type_nodes: dict[NodeType, OwnedDict[Node,"Repository"]]
    """プロジェクトの辞書"""

    services: OwnedDict[Service,"Repository"]
    """サービスの辞書"""

    types: OwnedDict[NodeType,"Repository"]
    """ノードタイプの辞書"""

    tags: OwnedDict[Tag,"Repository"]
    tag_names: dict[str, Tag | list[Tag]]

    states:OwnedDict[State,"Repository"]

    #
    # Accessors
    #
            
    def tag(self, name: str) -> Tag | None:
        """タグを取得します。"""
        names = name.split(".")
        if names[-1] in self.tag_names:
            x = self.tag_names[name]
            if not isinstance(x, list):
                return x
            else:
                for y in x:
                    if y.match(names):
                        return y
        return None
    def all_tags(self)->Iterable[Tag]:
        for x in self.tags.values():
            yield from x.walk()
    def tag_or_create(self,name:str,parent:Tag|None)->Tag:
        tag=self.tag(name)
        if tag is None:
            tag=Tag()
            tag.parent=parent
            tag.name=name
            self.add_tag(tag)
        return tag

    def nodes(self,type: NodeType | str | None=None)->Iterable[Node]:
        if isinstance(type, str):
            type = self.types[type]
        if type is None:
            return (y for x in self.type_nodes.values() for y in x.values())
        else:
            return self.type_nodes[type].values()

    def node(self, arg: str, type: NodeType | str | None) -> Node | None:
        if isinstance(type, str):
            type = self.types[type]
        sep=arg.find(":")
        if sep>=0:
            type=self.types[arg[0:sep]]
            arg=arg[sep+1:]
        if type is not None:
            return self.type_nodes[type].get(arg,None)
        else:
            ret:Node|None=None
            for type in self.types.values():
                n=self.type_nodes[type].get(arg,None)
                if n is not None:
                    if ret is not None:
                        raise KeyError(arg+": ambiguous name (in "+ret.type.name+" and "+type.name+").")
                    else:
                        ret=n
            return ret

    def node_or_error(self,arg:str,type:NodeType | str | None=None)->Node:
        """指定した条件のNodeを返します。"""
        ret=self.node(arg,type)
        if ret is None:
            raise KeyError(str(arg) + ": Node of that name is not found.")
        return ret

    #
    # Paths
    #
    config_dir: Path=Path()
    data_dir: Path=Path()
    dir: Path=Path()
    service_path: dict[str,str]
    node_path: QueryPathSelector
    node_service_path: QueryPathSelector

    DEFAULT_CONFIG_DIR = ".repository"
    DEFAULT_CONFIG_FILE = "config"
    DEFAULT_DATA_PATH = "../.data"
    DEFAULT_PATH = ".."
    DEFAULT_SERVICE_PATH = "{service}"
    DEFAULT_NODE_PATH = "{node}"
    DEFAULT_NODE_SERVICE_PATH = "{node}/{service}"

    def config_path(self, node:Node|None=None, service: Service|None=None)->Path:
        path=self.config_dir
        if node is None:
            if service is None:
                return path
            else:
                return path / service.name
        else:
            path=path / node.type.name / node.name
            if service is None:
                return path
            else:
                return path / service.name

    def data_path(self, service: Service|None=None)->Path:
        if service is None:
            return self.data_dir
        else:
            return self.data_dir / service.name

    def path(self, service: Service|None=None)->Path:
        path=self.dir
        if service is None:
            return path
        else:
            tmpl=self.service_path.get(service.name,None)
            if tmpl is None:
                tmpl=self.service_path.get("",self.DEFAULT_SERVICE_PATH)
            p=Path(tmpl.format(service=service.name))
        if p.is_absolute():
            return p
        else:
            return path / p
    
    def node_path_resolver(self)->Callable[[Node],Path]:
        return self.node_path.resolver(self)
    
    def node_service_path_resolver(self,service:Service)->Callable[[Node],Path]:
        return self.node_path.resolver(self,{"service":service.name})

    #
    # Initialization and configuration
    #

    def __init__(self) -> None:
        self.services = OwnedDict(self)
        self.types = OwnedDict(self)
        self.tags = OwnedDict(self)
        self.tag_names = {}
        self.states=OwnedDict(self)
        self.type_nodes=defaultdict(lambda :OwnedDict(self))
        self.query_interface=RepositoryQueryInterface(self)
        self.service_path={}
        self.node_path=QueryPathSelector(self,None, self.DEFAULT_NODE_PATH)
        self.node_service_path=QueryPathSelector(self,None, self.DEFAULT_NODE_SERVICE_PATH)

    def configure(self, data: Json = None) -> None:
        config:RepositoryConfig
        if data is None:
            data = self.DEFAULT_CONFIG_DIR
        if isinstance(data, str):
            dir = Path(data)
            if dir.is_file():
                dir = dir.parent
                file = dir
            else:
                file = dir / self.DEFAULT_CONFIG_FILE
            config = cast(RepositoryConfig,load_config_file(file, Repository.CONFIG_SCHEMA))
            if "config_path" not in config:
                config["config_path"] = str(dir)
        else:
            config=cast(RepositoryConfig,data)
        if "config_path" in config:
            self.config_dir=Path(config["config_path"])

        def _resolve_path(config:str|None,root:Path,default:str)->Path:
            if config is None:
                p=Path(default)
            else:
                p=Path(config)
            if p.is_absolute():
                return p
            else:
                return (root / p).resolve()
        self.data_dir=_resolve_path(config.get("data_path"),self.config_dir,self.DEFAULT_DATA_PATH)
        self.dir=_resolve_path(config.get("path"),self.config_dir,self.DEFAULT_PATH)
        sp=config.get("service_path",self.DEFAULT_SERVICE_PATH)
        if isinstance(sp,str):
            self.service_path={"":sp}
        else:
            self.service_path=sp
        self.node_path.add_dict(config.get("node_path"),self)
        self.node_service_path.add_dict(config.get("node_service_path"), self)

        # object creation
        self._create_tags(config.get("tags",None))
        self._create_nodetypes(config.get("types",None))
        self._create_services(config.get("services",None))
        self._create_states(config.get("states",None))
        self._create_nodes()

    def _create_nodetypes(self,config:dict[str,Json]|None)->None:
        self.types.clear()
        for obj in load_object_static(config,NodeType):
            self.add_nodetype(obj)

    def _create_tags(self, config: TagConfig|None) -> None:
        self.tags.clear()
        for tag in Tag.configure(config):
            self.add_tag(tag)

    def _create_services(self, config: dict[str,str|JsonObject]|None):
        """サービスを作成します。"""
        self.services.clear()
        for service in load_object(config,Service):
            self.add_service(service)

    def _create_states(self, config: dict[str,Json]|None):
        """状態を作成します。"""
        self.states.clear()
        if config is None:
            return
        for state in load_object_static(config,State):
            self.add_state(state)
    def _create_nodes(self) -> None:
        """Nodeを作成します。"""
        cfgs: list[tuple[Node, JsonObject]] = []
        for type in self.types.values():
            path = self.config_dir / type.name
            nodes=self.type_nodes[type]
            nodes.clear()
            schema=type.node_config_schema()
            if path.is_dir():
                for p in path.iterdir():
                    file:Path|None=None
                    if is_config_file(p):
                        file=p
                    elif p.is_dir():
                        file=config_file_of(p / type.name)
                    if file is not None:
                        cfg=cast(JsonObject,load_config_file(file,schema))
                        node=Node(type)
                        node.name=p.stem
                        self.add_node(node)
                        cfgs.append((node,cfg))
        for node, cfg in cfgs:
            node.configure(cfg)
    
    def refresh(self):
        """NodeTypeの内容が変わったとき呼ばれます。"""
        self.node_path.refresh(self)
        self.node_service_path.refresh(self)

    #
    # Construction by code
    #
    def add_nodetype(self,obj:NodeType):
        self.types[obj.name]=obj
    def add_service(self,obj:Service):
        self.services[obj.name] = obj
    def add_tag(self,obj:Tag):
        if obj.parent is None:
            self.tags[obj.name]=obj
        else:
            obj.parent.children[obj.name]=obj
        for x in obj.walk():
            x.assign(self,x.name)
            if x.name in self.tag_names:
                lst=self.tag_names[x.name]
                if isinstance(lst,list):
                    if x not in lst:
                        lst.append(x)
                else:
                    if x!=lst:
                        self.tag_names[x.name]=[x,lst]
            else:
                self.tag_names[x.name]=x
    def add_state(self,obj:State):
        self.states[obj.name]=obj
    def add_node(self,obj:Node):
        self.type_nodes[obj.type][obj.name]=obj

    #
    # Queries
    #
    query_interface:RepositoryQueryInterface
    def query(self,query:str|Query)->Executor:
        if isinstance(query,str):
            query=Query(query,self)
        exec= query.apply(self.query_interface)
        if exec.iterable:
            return exec
        else:
            return AndExecutor(AllExecutor(self),[exec])

    #
    # Actions
    #
    @contextmanager
    def run(self, *nodes: Node):
        """Repositoryに何らかの操作をするときに、with文で使います。"""
        self.init(*nodes)
        yield
        self.close()

    def init(self, *nodes: Node):
        """Repositoryに何らかの操作をする前に呼びます。"""
        for s in self.services.values():
            s.init()

    def close(self):
        """Repositoryへの操作が終わった後に呼びます。"""
        for s in self.services.values():
            s.close()

    def update(self, *nodes: Node, intensive:bool=False):
        """各サービスで必要とする処理をします。"""
        for s in self.services.values():
            s.update(*nodes)

class QueryPathSelector(QuerySelector[str]):
    def resolver(self,repo:Repository,args:dict[str,Any]={}):
        qs=self.apply(repo.query_interface)
        def f(node:Node)->Path:
            tmpl=qs(node)
            return repo.dir / tmpl.format(node=node.name,type=node.type.name,**args)
        return f

class NotifyRepositoryStructureChanged(Protocol):
    def refresh(self,repo:Repository):...
