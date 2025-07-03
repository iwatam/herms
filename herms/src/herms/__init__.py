"""
hermsのコアモジュールです。

hermsが起動されると、アプリケーション全体を表す :class:`.App` クラスのサブクラスのオブジェクトが1つ作成されます。
:class:`.App` クラスは操作対象となる:class:`.Repository`を(場合によっては複数)持ちます。

:class:`Repository`は、管理対象となる以下のものを持ちます。
* :class:`Node` : hermsの利用対象となるもの
* :class:`NodeType` : :class:`Node`の定義
* :class:`Service` : 各:class:`Node`に対して

* :class:`.Plugin` : アプリケーション全体の動作を拡張します。
* :class:`.Project` : 個々のプロジェクトです。
* :class:`.Service` : 個々のプロジェクトに対して機能を提供します。
* :class:`.State` : プロジェクトに対してそれぞれの機能をどう提供するかを指定します。

"""


from .query import Query
from .handler import apply, use
from .job import Job
from .node import Node
from .nodetype import NodeType
from .app import App
from .cli import CliApp
from .repository import Repository,RepositoryConfig
from .service import Service
from .tag import Tag
from .state import State
from .config import Json,JsonObject,JsonSchema

__all__ = [
    "App",
    "CliApp",
    "Repository","RepositoryConfig",
    "Service",
    "Query",
    "Node",
    "NodeType",
    "Tag",
    "State",
    "Json","JsonObject","JsonSchema",
    "Job",
    "use",
    "apply",
]
