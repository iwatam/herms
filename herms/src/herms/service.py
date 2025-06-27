# -*- coding: utf-8 -*-
"""プロジェクトに機能を提供します。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import ClassVar

from .state import State
from .config import Json, JsonSchema
from .base import InRepository
from .node import Node

class Service(InRepository):
    """様々なサービスを提供します。

    システムは、各サービスに次のものを提供します。
    * サービスの設定
    * 各ノードの設定
    * 各ノードのデータ
    * サービスが利用するファイルスペース

    """

    CONFIG_SCHEMA:ClassVar[JsonSchema]={
        "type":"object",
        "properties":{
            "type":{"type":"string"},
            "description":{"type":"string"}
        }
    }


    def __init__(self):
        pass

    #
    # Configuration
    #
    NODE_DATA_SCHEMA = None

    def configure(self, data: Json) -> None:
        """設定を適用します。"""
        _=data

    def node_config_schema(self)->JsonSchema:
        return {"type":"object"}


    #
    # path
    #
    def module_path(self)->Path|None:
        """
        モジュールのパスを返します。
        """
        mod = sys.modules[self.__class__.__module__]
        if mod.__file__ is None:
            return None
        else:
            return Path(mod.__file__).parent

    def _find_file_in(self, dir: Path, file: str | None) -> Path:
        if file is None:
            return dir
        if dir.is_dir():
            return dir / file
        else:
            return dir.parent / (dir.name + "." + file)

    def config_path(
        self, node: Node | None = None, file: str | None = None
    ) -> Path | None:
        """サービスの設定ファイルのパスを返します。

        サービスの設定ディレクトリがあれば、その中の指定の名前のファイルを返します。
        なければ、サービス名を頭につけたファイルを返します。

        パスを指定しない場合は、サービスの設定ディレクトリを返します。存在しない場合はNoneを返します。
        """
        dir = self.owner.config_path(None,self)
        if node is not None:
            dir = dir / node.name
        return self._find_file_in(dir, file)

    def data_path(self, node: Node | None = None) -> Path:
        """サービスのデータディレクトリのパスを返します。

        nodeを指定した場合はそのノードに対応したデータディレクトリを返します。
        """
        dir = self.owner.data_path(self)
        if node is not None:
            dir = dir / node.name
        return dir

    #
    # Basic operation
    #
    def __hash__(self):
        return hash(self.name)

    #
    # Utilities
    #

    #
    # interface that must be overriden
    #
    ACTIVE='active'
    def supported_state(self) -> list[str]:
        """この Service に適用できる状態のリストを返します。"""
        return [Service.ACTIVE]

    def init(self):
        """
        初期化をします。

        起動時に1回呼ばれます。
        """
        pass

    def close(self):
        """終了処理をします。

        終了時に1回呼ばれます。
        """
        pass

    def update(self, *node:Node,intensive:bool=False):
        """各サービスの処理を実行します。
        """
        pass

    def state(self, *node:Node,oldstate:str,newstate:str):
        """状態が変更されたときの処理を行います。

        """
        pass
