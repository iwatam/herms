from herms import Repository
from herms.query import Query,QuerySelector
from .sample_repo import add_nodes, repo
import pytest

_=repo

@pytest.fixture
def data(repo:Repository):
    add_nodes(repo,{
        "type1":{
            "n11":{
                "properties":{
                    "foo":"n21",
                    "bar":["n31"],
                    "val":4
                },
                "tags":["tag1","t2"],
                "state":"s1"
            },
            "n12":{
                "properties":{
                    "foo":"n21",
                    "bar":["n31","n32"],
                    "val":6
                },
                "state":"s1"
            }
        },
        "type2":{
            "n21":{
                "properties":{
                    "text":["text1"],
                    "num":10
                },
                "state":"s1"
            },
            "n22":{
                "properties":{
                    "text":["text1","text2"],
                    "num":12
                },
                "tags":["tag2"],
                "state":"s1"
            },
            "n23":{
                "properties":{
                    "num":12
                },
                "state":"s1"
            },
            "n24":{
                "properties":{
                    "num":13
                },
                "state":"s1"
            },
            "n25":{
                "properties":{
                    "num":14
                },
                "state":"s1"
            }
        },
        "type3":{
            "n31":{
                "properties":{
                    "tagcat":["t1","t2"],
                    "tag":"tag2"
                },
                "state":"s1"
            },
            "n32":{
                "properties":{
                    "tagcat":["t1"],
                    "tag":"tag1"
                },
                "state":"s1"
            }
        }
    })

    yield repo

def test_query_grammar(repo:Repository):
    assert str(Query("foo.num>3",repo))==">(foo.num,3)"

def test_query_simple(data:Repository):
    q=Query("",data)
    assert str(q)=="All"
    assert [x.name for x in data.query(q).items()]==["n11","n12","n21","n22","n23","n24","n25","n31","n32"]

def test_query_type(data:Repository):
    q=Query("type1",data)
    assert str(q)=="type1"
    assert [x.name for x in data.query(q).items()]==["n11","n12"]

def test_query_tag(data:Repository):
    q=Query("tag1",data)
    assert str(q)=="tag1"
    assert [x.name for x in data.query(q).items()]==["n11","n32"]

    q=Query("tag2",data)
    assert [x.name for x in data.query(q).items()]==["n22","n31"]

    q=Query("t2",data)
    assert [x.name for x in data.query(q).items()]==["n11","n31"]

    q=Query("tagcat",data)
    assert [x.name for x in data.query(q).items()]==["n11","n31","n32"]

def test_query_simple_rel(data:Repository):
    q=Query("val=6",data)
    assert str(q)=="=(val,6)"
    assert [x.name for x in data.query(q).items()]==["n12"]

    q=Query("val=4,6",data)
    assert [x.name for x in data.query(q).items()]==["n11","n12"]

    q=Query("val<6",data)
    assert [x.name for x in data.query(q).items()]==["n11"]

    q=Query("val<=6",data)
    assert [x.name for x in data.query(q).items()]==["n11","n12"]

    q=Query("val>4",data)
    assert [x.name for x in data.query(q).items()]==["n12"]

    q=Query("text==\"text1\"",data)
    assert [x.name for x in data.query(q).items()]==["n21","n22"]

def test_query_logical(data:Repository):
    q=Query("text=text1 & num!=10",data)
    assert str(q)=="&(=(text,text1),!=(num,10))"
    assert [x.name for x in data.query(q).items()]==["n22"]

    q=Query("type2 & !(num>11 & num<=13) | type3",data)
    assert [x.name for x in data.query(q).items()]==["n21","n25","n31","n32"]

def test_query_selector(data:Repository):
    qs=QuerySelector(data,{"type1":"thisisType1","num>11 & num<=13":"num"},"None")
    f=qs.apply(data.query_interface)

    result={
        "n11":"thisisType1",
        "n12":"thisisType1",
        "n21":"None",
        "n23":"num"
    }
    for name,value in result.items():
        n=data.node(name,None)
        assert n is not None
        assert f(n)==value