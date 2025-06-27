import json
from pathlib import Path
from typing import ClassVar, Iterable, Protocol, Type, TypeVar, TypedDict, cast

from .loader import find_class
import yaml
import jsonschema

SUFFIXES = [".json", ".yaml", ".yml"]

type Json=None | str | int | float | bool | list[Json] | JsonObject
type JsonObject=dict[str,Json]
type JsonSchema=JsonObject

def is_config_file(file: Path) -> bool:
    for suffix in SUFFIXES:
        if file.suffix == suffix:
            return True
    return False


def config_file_of(file: Path) -> Path | None:
    """設定ファイルか存在するかどうかを判定します。

    file に拡張子 .json, .yaml, .yml のいずれかを足したファイルがある場合は、そのファイルを返します。それ以外の場合はNoneを返します。
    """
    if is_config_file(file) and file.exists():
        return file
    for suffix in SUFFIXES:
        f = file.with_suffix(suffix)
        if f.exists():
            return f
    return None

def load_config_file(file: Path, schema: JsonSchema) -> Json:
    """設定ファイルを読み込みます。

    拡張子にあわせて、JSONまたはYAMLを読み込みます。
    """
    ret: Json
    f = config_file_of(file)
    if f is None:
        ret = {}
    elif f.suffix == ".json":
        with open(f, "r") as f:
            ret = json.load(f)
    else:
        with open(f, "rb") as f:
            ret = yaml.safe_load(f)
    jsonschema.validate(ret,schema)
    return ret

class TypedConfig(TypedDict):
    type:str
class Configurable(Protocol):
    CONFIG_SCHEMA: ClassVar[JsonSchema]
    name:str
    def configure(self,data:Json): ...

CONFIGURABLE_SCHEMA:JsonSchema={
        "type":"object",
        "additionalProperties":{
            "items":{
                "anyOf":[{"type":"string"},
                {"type":"object",
                "properties":{
                    "type":{"type":"string"}
                },
                "required":["type"]}
                ]
            }
        }
    }

OBJ=TypeVar("OBJ",bound=Configurable)
def load_object(config: dict[str,str|JsonObject]|None,type:Type[OBJ])->Iterable[OBJ]:
    """サービスを作成します。"""
    if config is None:
        return
    jsonschema.validate(config,CONFIGURABLE_SCHEMA)
    objs:list[tuple[OBJ,JsonObject|None]]=[]
    for name, cfg in config.items():
        typename:str
        c:JsonObject|None
        if isinstance(cfg, str):
            typename = cfg
            c=None
        else:
            typename = cast(str,cfg["type"])
            c=cfg
        cls = find_class(typename, type)
        obj: OBJ = cls()
        obj.name=name
        objs.append((obj,c))
        yield obj
    for obj, cfg in objs:
        if cfg is not None:
            jsonschema.validate(cfg,type.CONFIG_SCHEMA)
        obj.configure(cfg)

def load_object_static(config: dict[str,Json]|None,cls:Type[OBJ])->Iterable[OBJ]:
    """オブジェクトを作成します。"""
    if config is None:
        return
    objs:list[tuple[OBJ,Json]]=[]
    for name, cfg in config.items():
        obj: OBJ = cls()
        obj.name=name
        objs.append((obj,cfg))
        yield obj
    for obj, cfg in objs:
        if cfg is not None:
            jsonschema.validate(cfg,cls.CONFIG_SCHEMA)
        obj.configure(cfg)
