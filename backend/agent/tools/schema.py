"""Function Calling 工具 schema 自动生成器。

从 TOOL_REGISTRY 各函数的类型注解 + docstring 生成 OpenAI 兼容的 tools schema，
与 MCP input_schema（均由函数签名推导）保持同源，一处改签名两处同步生效
（ADR-009 §5「schema 单一来源」）。

生成规则：
- 参数 JSON 类型由 typing 注解映射（str→string / int→integer / float→number /
  bool→boolean / list[X]→array / dict→object）
- 无默认值的参数进入 required；有默认值的可选（含 X | None 可空）
- 参数描述取自函数 docstring 的 Args 段（项目注释规范 P1 统一格式），缺失时回退参数名
- description 取函数 docstring 首行

消费方：agent/chat/orchestrator.py（对话链路，支持按 category 裁剪）。
"""

import inspect
import re
import typing
from collections.abc import Callable
from types import UnionType

# 定位 docstring 中 Args 段（到 Returns/Raises/Yields 或结尾为止）
_ARGS_SECTION_RE = re.compile(r"Args:\n(.*?)(?:\n\s*(?:Returns|Raises|Yields):|\Z)", re.S)
# Args 段内的单行参数项：`name: 描述`
_ARGS_ITEM_RE = re.compile(r"^\s+(\w+):\s+(.+)$", re.M)


def _parse_arg_descriptions(fn: Callable) -> dict[str, str]:
    """从函数 docstring 提取参数名 → 描述 映射。

    Args:
        fn: 目标函数。

    Returns:
        dict[str, str]: 参数名到一行描述的映射；无 Args 段或未命中时为空。
    """
    doc = inspect.getdoc(fn) or ""
    section = _ARGS_SECTION_RE.search(doc)
    if not section:
        return {}
    return {m.group(1): m.group(2).strip() for m in _ARGS_ITEM_RE.finditer(section.group(1), re.M)}


def _type_to_schema(tp: typing.Any) -> dict:
    """Python 类型注解 → JSON Schema 片段（OpenAI function parameters 子项）。

    Args:
        tp: typing 注解对象。

    Returns:
        dict: JSON Schema 片段，如 {"type": "string"} / {"type": "array", "items": ...}。
    """
    if tp is str:
        return {"type": "string"}
    if tp is int:
        return {"type": "integer"}
    if tp is float:
        return {"type": "number"}
    if tp is bool:
        return {"type": "boolean"}
    if tp is dict:
        return {"type": "object"}
    origin = typing.get_origin(tp)
    args = typing.get_args(tp)
    if origin in (list, typing.List):
        item = _type_to_schema(args[0]) if args and args[0] is not type(None) else {"type": "string"}
        return {"type": "array", "items": item}
    if origin in (typing.Union, UnionType):
        non_none = [a for a in args if a is not type(None)]
        if non_none:
            return _type_to_schema(non_none[0])
        return {"type": "null"}
    if origin is dict or origin is typing.Dict:
        return {"type": "object"}
    return {"type": "object"}


def _build_tool_definition(name: str, fn: Callable) -> dict:
    """为单个工具函数生成 OpenAI Function Calling 定义。

    Args:
        name: 工具名（TOOL_REGISTRY 键）。
        fn: 工具函数。

    Returns:
        dict: {"type": "function", "function": {name, description, parameters}}。
    """
    sig = inspect.signature(fn)
    hints = typing.get_type_hints(fn)
    descriptions = _parse_arg_descriptions(fn)

    properties: dict[str, dict] = {}
    required: list[str] = []
    for pname, param in sig.parameters.items():
        if pname in ("self", "cls"):
            continue
        prop = dict(_type_to_schema(hints.get(pname)))
        prop["description"] = descriptions.get(pname, pname)
        properties[pname] = prop
        if param.default is inspect.Parameter.empty:
            required.append(pname)

    first_line = (inspect.getdoc(fn) or name).strip().splitlines()[0]
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": first_line,
            "parameters": {"type": "object", "properties": properties, "required": required},
        },
    }


def build_tool_definitions(categories: set[str] | None = None, exclude: set[str] | None = None) -> list[dict]:
    """从 TOOL_REGISTRY 自动生成全部（或指定分类/排除集）工具的 schema 列表。

    Args:
        categories: 只生成指定 category 的工具；None 表示全部（默认）。
        exclude: 显式排除的工具名集合（如对话链路不暴露 add_poi/remove_poi）；
            None 表示不排除（默认）。

    Returns:
        list[dict]: OpenAI tools 列表，按 TOOL_REGISTRY 注册顺序。
    """
    from backend.agent.tools import TOOL_CATEGORIES, TOOL_REGISTRY

    definitions: list[dict] = []
    for name, fn in TOOL_REGISTRY.items():
        if categories is not None and TOOL_CATEGORIES.get(name) not in categories:
            continue
        if exclude and name in exclude:
            continue
        definitions.append(_build_tool_definition(name, fn))
    return definitions
