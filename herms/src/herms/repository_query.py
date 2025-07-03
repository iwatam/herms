
from __future__ import annotations
from collections.abc import Iterable
import sys
from typing import TYPE_CHECKING, Any, cast

from .datatype import DataType
from .tag import Tag
from .nodetype import NodeType,Property
from .node import Node
from .query import Props, ApplyExpr, Executor, NameExpr, NodeTypeExpr, Value, QueryFormatException, QueryInterface, LogicalExpr, RelExpr, StateExpr

if TYPE_CHECKING:
    from .repository import Repository
    from .state import State

class AndExecutor(Executor):
    first:Executor
    args:list[Executor]
    def __init__(self,first:Executor,args:list[Executor]):
        self.first=first
        self.args=args
        self.iterable=self.first.iterable

    def len(self)->int:
        return self.first.len()

    def items(self)->Iterable[Node]:
        for node in self.first.items():
            if self._match_args(node):
                yield node

    def match(self,node:Node)->bool:
        return self.first.match(node) and self._match_args(node)

    def _match_args(self,node:Node)->bool:
        return all((x.match(node) for x in self.args))

class OrExecutor(Executor):
    args:list[Executor]
    cond_args:list[Executor]
    def __init__(self,exprs:Iterable[Executor]):
        self.args=[]
        self.cond_args=[]
        for x in exprs:
            if x.iterable:
                self.args.append(x)
            else:
                self.cond_args.append(x)
        self.iterable=not self.cond_args

    def len(self)->int:
        if self.cond_args:
            return super().len()
        else:
            len_sum=0
            for x in self.args:
                len=x.len()
                if len==sys.maxsize:
                    return len
                len_sum+=len
            return len_sum

    def items(self)->Iterable[Node]:
        assert self.iterable
        ret:set[Node]=set()
        for expr in self.args:
            for x in expr.items():
                if x not in ret:
                    ret.add(x)
                    yield x

    def match(self,node:Node)->bool:
        return any((x.match(node) for x in self._all_args()))

    def _all_args(self)->Iterable[Executor]:
        yield from self.args
        yield from self.cond_args

class NotExecutor(Executor):
    arg:Executor
    def __init__(self,arg:Executor):
        self.arg=arg
    def match(self,node:Node)->bool:
        return not self.arg.match(node)

class AllExecutor(Executor):
    repo:Repository
    _len:int
    def __init__(self,arg:Repository):
        self.repo=arg
        self.iterable=True
        self._len=sum((len(x) for x in self.repo.nodes.values()))

    def match(self, node: Node) -> bool:
        return True
    
    def len(self) -> int:
        return self._len
    
    def items(self) -> Iterable[Node]:
        return self.repo.nodes.iterate()

class NodeTypeExecutor(Executor):
    nodetype:NodeType
    _len:int
    def __init__(self,arg:NodeType):
        self.nodetype=arg
        self.iterable=True
        self._len=len(arg.owner.nodes[self.nodetype])

    def match(self, node: Node) -> bool:
        return self.nodetype in node.type.ancestors()
    
    def len(self) -> int:
        return self._len
    
    def items(self) -> Iterable[Node]:
        return self.nodetype.owner.nodes.iterate(self.nodetype)

class NodeExecutor(Executor):
    node:Node
    def __init__(self,node:Node):
        self.node=node
        self.iterable=True
    def match(self, node: Node) -> bool:
        return node==self.node
    
    def len(self) -> int:
        return 1
    
    def items(self) -> Iterable[Node]:
        yield self.node

class StateExecutor(Executor):
    state:State
    def __init__(self,state:State):
        self.state=state
    def match(self, node: Node) -> bool:
        return node.state==self.state
class TagExecutor(Executor):
    tag:Tag
    def __init__(self,tag:Tag):
        self.tag=tag
    def match(self, node: Node) -> bool:
        return any((tag.isa(self.tag) for tag in node.tags))
class PropExecutor(Executor):
    props:Props
    def __init__(self,props:Props):
        self.props=props
    def value(self,node:Node)->list[tuple[Any,DataType]]:
        nodes:list[Node]=[node]
        values:list[tuple[Any,DataType]]=[]
        for rev,props in self.props.props:
            values.clear()
            for n in nodes:
                v=self._value_of(n,rev,props)
                values.extend(v)
            nodes=[x for x in values if isinstance(x,Node)]
        return values
    def _value_of(self,node:Node,rev:bool,prop:Property|dict[NodeType|None,Property])->Iterable[tuple[Any,DataType]]:
        if rev:
            if isinstance(prop,Property):
                props=[prop]
            else:
                props=prop.values()
            for p in props:
                ret=node.properties_rev.get(p)
                if ret is not None:
                    yield from ((x,p.type) for x in ret)
        else:
            p=prop if isinstance(prop,Property) else prop.get(node.type)
            if p is not None:
                if p.list:
                    lst=node.properties.get(p)
                    if lst is not None:
                        yield from ((x,p.type) for x in lst)
                else:
                    ret=node.properties.get(p)
                    if ret is not None:
                        yield (ret,p.type)

class ApplyExecutor(PropExecutor):
    op:ApplyExpr.Op
    cond:Executor
    def __init__(self,props:Props,op:ApplyExpr.Op,cond:Executor):
        super().__init__(props)
        self.op=op
        self.cond=cond

    def match(self,node:Node)->bool:
        values=self.value(node)
        if self.op=='&':
            return all((self.cond.match(x[0]) for x in values if isinstance(x,Node)))
        else:
            return any((self.cond.match(x[0]) for x in values if isinstance(x,Node)))

class RelExecutor(PropExecutor):
    op:str
    val:list[Value]
    def __init__(self,props:Props,op:str,val:list[Value]):
        super().__init__(props)
        self.op=op
        self.val=val

    def match(self,node:Node)->bool:
        values=self.value(node)
        if self.op.startswith('&'):
            return all((self._match(x,node.owner) for x in values))
        else:
            return any((self._match(x,node.owner) for x in values))
    def _match(self,value:tuple[Any,DataType],repo:Repository):
        op=self.op
        if op[0]=='&' or op[0]=='|':
            op=op[1:]
        if op=='!=':
            return all((value[0]!=x.value(repo,value[1]) for x in self.val))
        elif op=='=' or op=='==':
            return any((value[0]==x.value(repo,value[1]) for x in self.val))
        else:
            eq=op[-1]=='='
            val=self.val[0].value(repo,value[1])
            if op[0]=='>':
                return value[0]>val or (eq and value[0]==val)
            else:
                return value[0]<val or (eq and value[0]==val)


class RepositoryQueryInterface(QueryInterface):
    repo:Repository
    def __init__(self,repo:Repository):
        self.repo=repo

    def handle_logical_expr(self, query: LogicalExpr) -> Executor:
        if query.op=='!':
            return NotExecutor(query.args[0].apply(self))
        elif query.op=="&":
            first:Executor|None=None
            minlen=sys.maxsize
            args:list[Executor]=[]
            for x in query.args:
                c=x.apply(self)
                if c.iterable:
                    len=c.len()
                    if len<minlen:
                        first=c
                        minlen=len
                else:
                    if first is None:
                        first=c
                if first!=c:
                    args.append(c)
            assert first is not None
            args=sorted((x for x in args if x!=first),key=lambda x: x.len())
            return AndExecutor(first,args)
        else:
            return OrExecutor((x.apply(self) for x in query.args))
    def handle_nodetype_expr(self, query: NodeTypeExpr) -> Executor:
        return NodeTypeExecutor(query.type)
    def handle_state_expr(self, query: StateExpr) -> Executor:
        return StateExecutor(query.state)
    def handle_name_expr(self, query: NameExpr) -> Executor:
        if query.ns is not None:
            node=self.repo.node_or_error(cast(str,query.name),query.ns)
            return NodeExecutor(node)
        else:
            if not isinstance(query.name,str):
                name=".".join(query.name)
                tag=self.repo.tag(name)
                if tag is None:
                    raise QueryFormatException(f"No tag found for '{name}'.")
                return TagExecutor(tag)
            else:
                node=self.repo.node(query.name,None)
                if node is not None:
                    return NodeExecutor(node)
                state=self.repo.states.get(query.name)
                if state is not None:
                    return StateExecutor(state)
                tag=self.repo.tag(query.name)
                if tag is None:
                    raise QueryFormatException(f"No node or tag found for '{query.name}'.")
                return TagExecutor(tag)
    def handle_apply_expr(self, query: ApplyExpr) -> Executor:
        return ApplyExecutor(query.props,query.op,query.condition.apply(self))
    def handle_rel_expr(self, query: RelExpr) -> Executor:
        return RelExecutor(query.props,query.op,query.val)