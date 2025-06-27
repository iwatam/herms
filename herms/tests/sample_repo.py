
from typing import cast
from herms import Node, Repository
from herms.config import JsonObject
from herms.node import NodeConfig
import pytest


@pytest.fixture
def repo():
    repo=Repository()
    repo.configure({
        "types":{
            "type1":{
                "properties":{
                    "foo":{
                        "type":"type2",
                        "list":False
                    },
                    "bar":{
                        "type":"type3",
                        "list":True
                    },
                    "val":{
                        "type":"int",
                        "list":False
                    }
                }
            },
            "type2":{
                "properties":{
                    "text":{
                        "type":"string",
                        "list":True
                    },
                    "num":{
                        "type":"int",
                        "list":False
                    }
                }
            },
            "type3":{
                "properties":{
                    "tagcat":{
                        "type":"tagcat",
                        "list":True
                    },
                    "tag":{
                        "type":"tag"
                    }
                }
            }
        },
        "tags":{
            "tag1":"test tag 1",
            "tag2":"test tag 2",
            "tagcat": {"children":["t1","t2","t3"]}
        },
        "states":{
            "s1":{},
            "s2":{},
            "s3":{}
        }
    })
    yield repo

def add_nodes(repo:Repository,config:dict[str,dict[str,NodeConfig]]):
    for typename,v in config.items():
        type=repo.types[typename]
        for name,cfg in v.items():
            node=Node(type)
            node.name=name
            repo.add_node(node)
    for typename,v in config.items():
        type=repo.types[typename]
        for name,cfg in v.items():
            node=repo.node(name,type)
            assert node is not None
            node.configure(cast(JsonObject,cfg))
