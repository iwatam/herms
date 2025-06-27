from __future__ import annotations

from typing import TYPE_CHECKING, Literal, TypedDict, cast, ClassVar

from .query import Query

from .base import InRepository
if TYPE_CHECKING:
    from .config import Json,JsonSchema
    from .repository import Repository
    from .service import Service

type ServiceStateConfig=str|dict[str,str|list[str]]

class StateConfig(TypedDict,total=False):
    description:str
    lifecycle:Literal['initial','final']
    condition:str
    transitions:dict[str,TransitionConfig|str|bool|None]
    services:ServiceStateConfig
class TransitionConfig(TypedDict):
    auto:bool
    condition:str

class State(InRepository):
    CONFIG_SCHEMA:ClassVar[JsonSchema]={
        "type":"object",
        "properties":{
            "description":{"type":"string"},
            "condition":{"type":"string"},
            "transitions":{
                "type":"object",
                "additionalProperties":{
                    "anyOf":[
                        {"type":"boolean"},
                        {"type":"string"},
                        {"type":"null"},
                        {"type":"object",
                         "properties":{
                             "auto":{"type":"boolean"},
                             "condition":{"type":"string"}
                         }}
                    ]
                }
            },
            "states":{
                "anyOf":[
                    {"type":"string"},
                    {"type":"object",
                    "additionalProperties":{
                        "anyOf":[
                            {"type":"string"},
                            {"type":"array","items":{"type":"string"}}
                        ]
                    }}
                ]
            }
        }
    }

    description:str=""
    condition:Query
    transitions:dict[State,Transition]
    services:dict[Service,str]
    lifecycle:bool|None=None

    def __init__(self):
        self.condition=Query()
        self.transitions={}
        self.services={}

    def refresh(self,repo:Repository):
        self.condition.refresh(repo)
        for tr in self.transitions.values():
            tr.refresh(repo)

    def configure(self,data:Json):
        if data is None:
            return
        elif isinstance(data,str):
            self.description=data
            return
        cfg=cast(StateConfig,data)
        self.description=cfg.get("description","")
        self.condition=Query(cfg.get("condition",""))
        if "lifecycle" in cfg:
            self.lifecycle=cfg.get("lifecycle")=='initial'
        self.transitions={}
        for name,c in cfg.get('transitions',{}):
            tostate=self.owner.states[name]
            tr=Transition()
            tr.fromstate=self
            tr.tostate=tostate
            tr.configure(c)
        services=cfg.get("services")
        if services is not None:
            if isinstance(services,str):
                for service in self.owner.services.values():
                    self.services[service]=services
            else:
                for val,slist in services.items():
                    if isinstance(slist,str):
                        slist=[slist]
                    for s in slist:
                        self.services[self.owner.services[s]]=val

class Transition:
    auto:bool
    condition:Query
    fromstate:State
    tostate:State

    def refresh(self,repo:Repository):
        self.condition.refresh(repo)
    
    def configure(self,data:Json):
        if isinstance(data,str):
            self.auto=True
            self.condition=Query(data)
        elif isinstance(data,bool):
            self.auto=data
            self.condition=Query()
        elif data is None:
            self.auto=False
            self.condition=Query()
        else:
            cfg=cast(TransitionConfig,data)
            self.auto=cfg.get('auto',False)
            self.condition=Query(cfg.get('condition',""))
