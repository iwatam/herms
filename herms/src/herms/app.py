from __future__ import annotations

import argparse
import sys
from argparse import Namespace, RawTextHelpFormatter
from pathlib import Path
from typing import Any, ClassVar, Self, TypedDict, cast


from .config import JsonObject, JsonSchema, load_config_file
from .repository import Repository

class AppConfig(TypedDict,total=False):
    repository:str|dict[str,str]
    default_repository:str

class App:
    """アプリケーションを表します。

    hermsが起動されるとき、このクラスのサブクラスのインスタンスが作成されます。

    :class:`App` のインスタンスを作るには、次の方法があります。

    * cli()を呼び出す
      コマンドラインから設定を読み込みます。
    * App()で作成し、configure()で設定する
      設定オブジェクトから設定を読み込みます。
    * App()で作成し、add_repository()で追加する
    
    TODO:
    複数repositoryの対応
    """
    CONFIG_SCHEMA:ClassVar[JsonSchema]={
        "type":"object",
        "properties":{
            "repository":{"type":"string"}
        }
    }


    DEFAULT_CONFIG_FILE = "herms"
    """作業用ディレクトリのパス"""


    repositories: list[Repository]
    """Repositoryのインスタンス"""


    def __init__(self) -> None:
        pass

    def configure(self, config: Any) -> None:
        """設定を適用します。

        Parameters
        ----------
        config : AppConfig
            設定オブジェクト
        """
        self.repository = Repository()
        self.repository.configure(config.get("repository",Repository.DEFAULT_CONFIG_DIR))

    def run(self) -> None:
        """
        実行します。
        """
        pass

    #
    # Command line interface
    #
    @classmethod
    def default_config_path(cls) -> str:
        return Repository.DEFAULT_CONFIG_DIR

    @classmethod
    def cli(cls, argv: list[str] = sys.argv[1:]) -> Self:
        """コマンドラインから呼び出され、処理をします。"""
        parser = cls.create_parser()
        cls.add_parser_arguments(parser)
        args = parser.parse_args(argv)
        app = cls()
        app.configure(cls.create_config(args))
        return app

    @classmethod
    def create_parser(cls) -> argparse.ArgumentParser:
        """コマンドライン引数を解析するためのArgumentParserを作成します。"""
        parser = argparse.ArgumentParser(
            description="an project management script.",
            formatter_class=RawTextHelpFormatter,
        )
        return parser

    @classmethod
    def add_parser_arguments(
        cls, parser: argparse.ArgumentParser
    ) -> argparse.ArgumentParser:
        """ArgumentParserに引数を追加します。"""
        parser.add_argument("-c", "--config", help="configuration file")
        parser.add_argument("-r", "--repository", help="target repository (location or NAME:LOCATION)")
        return parser

    @classmethod
    def create_config(cls, args: Namespace) -> JsonObject:
        """コマンドライン引数を解析します。"""

        if args.config:
            filename = Path(args.config)
        else:
            filename = Path(cls.default_config_path())
        if filename.is_dir():
            filename = filename / cls.DEFAULT_CONFIG_FILE
        data = load_config_file(filename, cls.CONFIG_SCHEMA)
        config:JsonObject
        if data is None:
            config={}
        else:
            config=cast(JsonObject,data)
        if args.repository:
            config["repository"] = args.repository
        return config
