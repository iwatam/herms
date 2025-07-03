from __future__ import annotations

import argparse
import asyncio
import builtins
import json
import logging
import sys
from typing import Any, Awaitable, Callable, Literal, TypeAlias, TypedDict, cast

import yaml

from .config import Json, JsonObject
from .query import Executor
from .handler import apply
from .app import App

CommandFunc: TypeAlias = Callable[
    [argparse.ArgumentParser], Callable[[argparse.Namespace], None|Awaitable[None]]
]


class CliAppConfig(TypedDict,total=False):
    loglevel: str | int
    """ログレベル"""

    args: list[str]
    """コマンドライン引数
    """


class CliApp(App):
    _parser: argparse.ArgumentParser
    _commands: dict[str, CommandFunc] = {}
    args: list[str] = []

    CONFIG_SCHEMA={
        "allOf":[
            App.CONFIG_SCHEMA,
            {"type":"object",
             "properties":{
                 "loglevel":{
                     "type":["string","integer"]
                 },
                 "args":{
                     "type":"array",
                     "items":{"type":"string"}
                 }
             }}
        ]
    }

    def configure(self, config: Json) -> None:
        """設定を適用します。
        """
        super().configure(config)
        cfg=cast(CliAppConfig,config)
        logging.basicConfig(level=cfg.get("loglevel",logging.WARNING))
        self.args = cfg.get("args",[])

    def run(self) -> None:
        """
        実行します。
        """

        for s in self.repository.services:
            apply(self, s)
        self.add_commands()

        parser = argparse.ArgumentParser(
            prog="herms",
            description="Command line interface of herms.",
            formatter_class=argparse.RawTextHelpFormatter,
        )
        commands = parser.add_subparsers(title="commands")

        for name, cmd in self._commands.items():
            p = commands.add_parser(name)
            f = cmd(p)
            p.set_defaults(func=f)
        parser.set_defaults(func=None)
        args = parser.parse_args(self.args)
        if args.func is not None:
            async def _():
                async with self.repository.run():
                    ret=args.func(args)
                    if ret is not None:
                        await ret
            asyncio.run(_())
        else:
            parser.print_help()

    #
    # protected interface
    #
    @classmethod
    def create_parser(cls) -> argparse.ArgumentParser:
        """コマンドライン引数を解析するためのArgumentParserを作成します。"""
        parser = argparse.ArgumentParser(description="an project management script.")
        return parser

    @classmethod
    def add_parser_arguments(
        cls, parser: argparse.ArgumentParser
    ) -> argparse.ArgumentParser:
        """コマンドライン引数を解析するためのArgumentParserを作成します。"""
        super().add_parser_arguments(parser)
        parser.add_argument(
            "-v", "--verbose", action="store_true", help="Verbose messaging"
        )
        parser.add_argument("-D", "--debug", action="store_true", help="Debug mode.")
        parser.add_argument("args", nargs=argparse.REMAINDER, help="Debug mode.")
        parser.epilog = "run with no argument to show command help."
        return parser

    @classmethod
    def create_config(cls, args: argparse.Namespace) -> JsonObject:
        """コマンドライン引数を解析します。"""
        config: JsonObject = super().create_config(args)
        if args.debug:
            config["loglevel"] = logging.DEBUG
        elif args.verbose:
            config["loglevel"] = logging.INFO
        config["args"] = args.args
        return config

    #
    # Commands
    #
    # usage
    # def COMMAND(...):...
    # @parser(COMMAND)
    # def PARSER(self,arg): ...

    # TODO: サービスコマンドと元々のコマンド
    def _add_command(self, func: CommandFunc, *names: str):
        for name in names:
            if name in self._commands:
                raise KeyError(name + ": A command with same name already exists.")
            self._commands[name] = func

    def command(self, name: str = "") -> Callable[[CommandFunc], CommandFunc]:
        def deco(f: CommandFunc):
            command_name = name or f.__name__
            self._add_command(f, command_name)
            return f

        return deco

    def add_commands(self):
        @self.command()
        def update(parser: argparse.ArgumentParser): # type: ignore
            parser.add_argument("-i", "--intensive", action="store_true", default=False)
            self.add_nodes_argument(parser)

            async def _(args: argparse.Namespace)->None:
                exec=self.get_nodes_from_args_or_none(args)
                if exec is None:
                    await self.repository.update(intensive=args.intensive)
                else:
                    await self.repository.update(*exec.items(), intensive=args.intensive)

            return _

        @self.command()
        def list(parser: argparse.ArgumentParser): # type: ignore
            parser.add_argument(
                "-f", "--format", choices=["csv", "json", "yaml"], default="yaml"
            )  # TODO no text formatter
            parser.add_argument("-p", "--property", action="append", default=[])
            self.add_nodes_argument(parser)

            async def _(args:argparse.Namespace):
                exec=self.get_nodes_from_args(args)
                sys.stdout.write(
                    self.format(
                        builtins.list(map(lambda x: x.name,exec.items())),
                        args.format,
                    )
                )

            return _

        @self.command()
        def state(parser: argparse.ArgumentParser): # type: ignore
            parser.add_argument(
                "state", choices=self.repository.states.keys()
            )
            self.add_nodes_argument(parser)

            async def _(args:argparse.Namespace):
                exec=self.get_nodes_from_args(args)
                await self.repository.state(*exec.items(),state=self.repository.states[args.state])

            return _
        @self.command()
        def config(parser: argparse.ArgumentParser): # type: ignore
            sub = parser.add_subparsers()

            def _expand(args: argparse.Namespace):
                pass

            p = sub.add_parser("expand")
            p.set_defaults(sub_func=_expand)
            sub.add_parser("collapse")
            def _(args:argparse.Namespace):
                args.sub_func()

            return _

    #
    # Utilities
    #
    def add_nodes_argument(self, parser: argparse.ArgumentParser):

        parser.add_argument("query", nargs="*", help="Node query")

    def get_nodes_from_args(self, args: argparse.Namespace) -> Executor:
        text=" ".join(args.query)
        return self.repository.query(text)

    def get_nodes_from_args_or_none(self, args: argparse.Namespace) -> Executor|None:
        text=" ".join(args.query)
        if text:
            return self.repository.query(text)
        else:
            return None
        
    def format(self, val: dict[Any,Any] | list[Any], type: Literal["json", "yaml", "csv"] = "json"):
        if type == "json":
            return json.dumps(val)
        elif type == "yaml":
            return yaml.dump(val)
        elif type == "csv":
            ret:list[str] = []
            if isinstance(val, dict):
                for k, v in val.items():
                    ret.append(str(k) + "," + ",".join(v) + "\n")
            else:
                for v in val:
                    ret.append(",".join(v) + "\n")
            return "".join(ret)
