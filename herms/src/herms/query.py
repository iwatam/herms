from __future__ import annotations

from abc import ABC, abstractmethod
import sys
from typing import  TYPE_CHECKING, Any, Callable, ClassVar, Generic, Iterable, Literal, TypeVar, cast

from lark import Lark, Token, Tree
from . import datatype
from .node import Node
from .nodetype import DataType, NodeType, Property

if TYPE_CHECKING:
    from .repository import Repository
    from .state import State

class QueryFormatException(Exception):
    def __init__(self, msg: str = "Syntax error"):
        super().__init__(msg)

class Query:
    """Nodeに対する条件式です。
    
    この条件式に基づいて、以下の2つのことができます。
    * あるNodeが条件に合致するかどうかを判別する
    * 条件に合致するすべてのNodeを取得する

    Queryは、まず構文解析を行い、Lark Treeに変換されます。その後、Repositoryの情報を
    使って、Expressionに変換されます。この変換では、NodeTypeとその中身が変化しないという
    仮定を用います。

    Expressionは、apply()を使ってExecutorに変換されます。この変換は、QueryInterfaceが行います。
    Executorは、Repositoryの中身が変化しない期間のみ有効です。
    """

    _parser = Lark(
        r"""
?start: cond_e* -> cond_or
?cond_e: cond_a ( "|" cond_a )* -> cond_or
?cond_a: cond_b ( "&" cond_b )* -> cond_and
?cond_b: cond
    | "!" cond_b -> cond_not
    | "(" cond_e ")"
cond: props rel -> cond_rel
    | props LOGIOP? "{" cond_e "}" -> cond_apply
    | (SYM | dotted | abs_id) -> cond_pred
rel: RELOP val
    | EQOP val ("," val)*
props: "."? prop ("." prop)*
prop: REV? SYM
val: SYM | STRING | dotted | abs_id
dotted: SYM ("." SYM)+
abs_id: SYM ":" SYM

%import common.ESCAPED_STRING -> STRING
%import common.WS
%ignore WS
SYM: /(\w|[-_])+/
REV: /~/
RELOP: /[&|]?[<>]=?/
EQOP: /[!=]?=/
LOGIOP: /[&|]/
"""
    )

    text: str
    tree:Tree[Token]|None=None
    expr: Expression

    def __init__(self,text: str="",repo:Repository|None=None):
        self.text=text
        if text:
            self.tree = Query._parser.parse(text)
            if repo is not None:
                self.refresh(repo)
        else:
            self.tree=None
            self.expr=Expression.All
    #
    # API
    #
    def __str__(self) -> str:
        return self.expr.__str__()
    
    def refresh(self,repo:Repository):
        """RepositoryのNodeType定義が変わったとき実行します。"""
        if self.tree is not None:
            self.expr=self._parse_cond(self.tree,repo) or Expression.Empty
    
    def apply(self,qi:QueryInterface)->Executor:
        return self.expr.apply(qi)
    
    def _parse_cond_children(self,tree:Tree[Token],repo:Repository)->list[Expression|None]:
        ret:list[Expression|None]=[]
        for x in tree.children:
            assert isinstance(x,Tree)
            ret.append(self._parse_cond(x,repo))
        return ret
    def _parse_cond(self,tree:Tree[Token],repo:Repository)->Expression|None:
        if tree.data=="cond_or":
            children=list(filter(None,self._parse_cond_children(tree,repo)))
            if len(children)==1:
                return children[0]
            return LogicalExpr("|",children)
        elif tree.data=="cond_and":
            children=list(filter(None,self._parse_cond_children(tree,repo)))
            if len(children)==1:
                return children[0]
            if all(children):
                return LogicalExpr("&",children)
            else:
                return None
        elif tree.data=="cond_not":
            child=next(iter(self._parse_cond_children(tree,repo)))
            if child is None:
                return Expression.All
            else:
                return LogicalExpr("!",[child])
        elif tree.data=="cond_pred":
            arg=tree.children[0]
            if isinstance(arg,Token):
                name=arg.value
                if name in repo.types:
                    return NodeTypeExpr(repo.types[name])
                if name in repo.states:
                    return StateExpr(repo.states[name])
                return NameExpr(arg.value,None)
            elif arg.data=="abs_id":
                ns=arg.children[0]
                name=arg.children[1]
                assert isinstance(ns,Token)
                assert isinstance(name,Token)
                return NameExpr(name.value,repo.types[ns.value])
            elif arg.data=="dotted":
                return NameExpr([x.value for x in arg.children if isinstance(x,Token)])
            else:
                assert False
        elif tree.data=="cond_rel":
            prop=self._parse_props(tree.children[0],repo,False)
            rel=tree.children[1]
            assert isinstance(rel,Tree)
            op=rel.children[0]
            assert isinstance(op,Token)
            val=[self._parse_val(x,prop.type(),repo) for x in rel.children[1:]]
            ret=RelExpr(prop,op.value,val)
            return ret
        elif tree.data=="cond_apply":
            prop=self._parse_props(tree.children[0],repo,True)
            if len(tree.children)>2:
                op=cast(ApplyExpr.Op,cast(Token,tree.children[1]).value)
            else:
                op="|"
            cond=tree.children[-1]
            assert isinstance(cond,Tree)
            cond_expr=self._parse_cond(cond,repo)
            if cond_expr is None:
                return None
            ret=ApplyExpr(prop,op,cond_expr)
            return ret
        else:
            assert False
    def _parse_val(self,tree:Tree[Token]|Token,type:DataType,repo:Repository)->Value:
        if isinstance(tree,Token):
            if tree.type=="STRING":
                text=tree.value[1:-1].encode().decode('unicode_escape')
            else:
                text=tree.value
            if type is None:
                return DynamicValue(text)
            else:
                return Value(datatype.decode(text,type,repo))
        elif tree.data=="dotted":
            return Value(repo.tag(".".join((cast(Token,x).value for x in tree.children))))
        elif tree.data=="abs_id":
            ns=tree.children[0]
            name=tree.children[1]
            assert isinstance(ns,Token)
            assert isinstance(name,Token)
            return Value(repo.node(name.value,repo.types[ns.value]))
        elif tree.data=="val":
            return self._parse_val(tree.children[0],type,repo)
        else:
            assert False
    def _parse_props(self,tree:Tree[Token]|Token,repo:Repository,is_node:bool)->Props:
        assert isinstance(tree,Tree)
        args:list[tuple[bool,str]]=[]
        for x in tree.children:
            assert isinstance(x,Tree)
            rev= len(x.children)>1
            propname=x.children[-1]
            assert isinstance(propname,Token)
            propname=propname.value
            args.append((rev,propname))
        return Props(args,repo,is_node)

class Props:
    type Prop=tuple[bool,dict[NodeType|None,Property]|Property]
    props:list[Prop]
    def __init__(self,names:list[tuple[bool,str]],repo:Repository,is_node:bool):
        ret:list[Props.Prop]=[]
        types:list[NodeType]|None=None

        index=len(names)
        for rev,propname in names:
            index-=1

            props:dict[NodeType|None,Property]={}
            newtypes:list[DataType]=[]
            for type in repo.types.values():
                prop=type.properties.get(propname)
                if prop is None or ((is_node or index>0) and not prop.is_node()):
                    continue
                if rev:
                    totype=prop.owner
                    if isinstance(prop.type,NodeType):
                        fromtype=prop.type
                    elif prop.type=="node":
                        fromtype=None
                    else:
                        continue
                else:
                    fromtype=prop.owner
                    totype=prop.type
                if types is not None and fromtype not in types:
                    continue

                props[fromtype]=prop
                newtypes.append(totype)

            if len(props)==0:
                raise QueryFormatException(f"{propname}: Property not found or type mismatch.")
            elif len(props)==1:
                ret.append((rev,next(iter(props.values()))))
            else:
                ret.append((rev,props))
            if "node" in newtypes:
                types=None
            else:
                types=[x for x in newtypes if isinstance(x,NodeType)]
        self.props=ret
    def type(self)->DataType:
        """このプロパティの返値の型を返します。
        
        Noneは型が動的にしか決まらないことを示します。"""
        last=self.props[-1][1]
        type:DataType=None
        if isinstance(last,Property):
            return last.type 
        else:
            for prop in last.values():
                t=prop.type
                if type is None:
                    type=t
                elif type==t:
                    pass
                elif datatype.is_node(t) and datatype.is_node(type):
                    type="node"
                elif datatype.is_tag(t) and datatype.is_tag(type):
                    type="tag"
                else:
                    return None
            return type
    def __str__(self) -> str:
        return ".".join((("~" if rev else "")+(
            val.name if isinstance(val,Property) else cast(Property,next(iter(val.keys()))).name
        ) for rev,val in self.props))
#
# Executor
#
class Executor:
    iterable:bool=False

    def match(self,node:Node)->bool:
        return True

    def len(self)->int:
        """要素のだいたいの数を返します。"""
        return sys.maxsize

    def items(self)->Iterable[Node]:
        """要素を返します。
        """
        assert False

#
# Expression tree
#
class Expression(ABC):
    All:ClassVar[Expression]
    Empty:ClassVar[Expression]

    @abstractmethod
    def apply(self,qi:QueryInterface)->Executor:...

class All(Expression):
    def __str__(self):
        return "All"
    def apply(self,qi:QueryInterface):
        return Executor()
Expression.All=All()

class Empty(Expression):
    class _Executor(Executor):
        def __init__(self):
            self.iterable=True

        def match(self,node:Node)->bool:
            return False

        def len(self)->int:
            return 0

        def items(self)->Iterable[Node]:
            """要素を返します。
            """
            return ()    
        def __str__(self):
            return "Empty"
    def apply(self,qi:QueryInterface):
        return Empty._Executor()
Expression.Empty=Empty()

class LogicalExpr(Expression):
    type Op=Literal['&','|','!']
    op:Op
    args:list[Expression]

    def __init__(self,op:Op,exprs:list[Expression]):
        self.op=op
        self.args=exprs
    def __str__(self)->str:
        return f"{self.op}({",".join((str(x) for x in self.args))})"
    def apply(self,qi:QueryInterface):
        return qi.handle_logical_expr(self)


class NodeTypeExpr(Expression):
    type:NodeType
    def __init__(self,type:NodeType):
        self.type=type

    def __str__(self)->str:
        return self.type.name
    def apply(self,qi:QueryInterface):
        return qi.handle_nodetype_expr(self)

class StateExpr(Expression):
    state:State
    def __init__(self,state:State):
        self.state=state

    def __str__(self)->str:
        return self.state.name
    def apply(self,qi:QueryInterface):
        return qi.handle_state_expr(self)

class NameExpr(Expression):
    name:str|list[str]
    ns:NodeType|None
    def __init__(self,name:str|list[str],ns:NodeType|None=None):
        self.name=name
        self.ns=ns

    def __str__(self)->str:
        if isinstance(self.name,str):
            name=self.name
        else:
            name=".".join(self.name)
        if self.ns is None:
            return name
        else:
            return self.ns.name+":"+name
    def apply(self,qi:QueryInterface):
        return qi.handle_name_expr(self)

class PropExpr(Expression):
    props:Props
    def __init__(self,props:Props):
        self.props=props
    def __str__(self)->str:
        return str(self.props)
    
class ApplyExpr(PropExpr):
    type Op=Literal['&','|']
    op:Op
    condition:Expression
    def __init__(self,prop:Props,op:Op,condition:Expression):
        super().__init__(prop)
        self.op=op
        self.condition=condition

    def __str__(self)->str:
        return f"{self.op}[{super().__str__()},{self.op},{self.condition}]"
    def apply(self,qi:QueryInterface):
        return qi.handle_apply_expr(self)

class RelExpr(PropExpr):
    op:str
    val:list[Value]
    def __init__(self,prop:Props,op:str,val:list[Value]):
        super().__init__(prop)
        self.op=op
        self.val=val
    def apply(self,qi:QueryInterface):
        return qi.handle_rel_expr(self)
    def __str__(self)->str:
        return f"{self.op}({super().__str__()},{",".join((str(x) for x in self.val))})"

class Value:
    """比較の対象となる値です。
    
    """
    val:Any
    def __init__(self,val:Any):
        self.val=val
    def value(self,repo:Repository,type:DataType)->Any:
        return self.val
    def __str__(self):
        return str(self.val)
class DynamicValue(Value):
    def value(self,repo:Repository,type:DataType)->Any:
        return datatype.decode(self.val,type,repo)
        

    
class QueryInterface(ABC):
    #
    # query
    #
    @abstractmethod
    def handle_logical_expr(self,query:LogicalExpr)->Executor: ...
    @abstractmethod
    def handle_nodetype_expr(self,query:NodeTypeExpr)->Executor: ...
    @abstractmethod
    def handle_state_expr(self,query:StateExpr)->Executor: ...
    @abstractmethod
    def handle_name_expr(self,query:NameExpr)->Executor: ...
    @abstractmethod
    def handle_rel_expr(self,query:RelExpr)->Executor: ...
    @abstractmethod
    def handle_apply_expr(self,query:ApplyExpr)->Executor: ...


T=TypeVar("T")
class QuerySelector(list[tuple[Query,T]],Generic[T]):
    default:T
    def __init__(self,repo:Repository,config:T | dict[str,T] | None,default:T):
        super().__init__()
        self.default=default
        if isinstance(config,dict):
            for k,v in cast(dict[str,T],config).items():
                if k=="" or k=="*":
                    self.default=v
                else:
                    self.append((Query(k,repo),v))
            
        elif config is not None:
            self.default=config
    
    def refresh(self,repo:Repository):
        """RepositoryのNodeType定義が変わったとき実行します。"""
        for v in self:
            v[0].refresh(repo)

    def apply(self,qi:QueryInterface)->Callable[[Node],T]:
        queries=[(q.apply(qi),v) for q,v in self]
        def _(node:Node)->T:
            for q,v in queries:
                if q.match(node):
                    return v
            return self.default
        return _
    def add(self,filter:Query,val:T):
        self.insert(0,(filter,val))
        
    def add_dict(self,val:dict[str,T]|T|None,repo:Repository):
        if val is None:
            return
        elif isinstance(val,dict):
            for k,v in cast(dict[str,T],val).items():
                self.add(Query(k,repo),v)
        else:
            self.default=val