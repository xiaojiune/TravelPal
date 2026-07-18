"""工具包：Agent 可调用的工具函数合集与注册表。"""

from collections.abc import Callable
from backend.agent.tools.poi import parse_biz_hours, poi_lookup

TOOL_REGISTRY: dict[str, Callable] = {
    "poi_lookup": poi_lookup,
}

__all__ = [
    "parse_biz_hours",
    "poi_lookup",
    "TOOL_REGISTRY",
]
