"""工具包：Agent 可调用的工具函数合集与注册表。"""

from collections.abc import Callable

from backend.agent.tools.plan import get_plan, get_plan_result
from backend.agent.tools.poi import parse_biz_hours, poi_lookup
from backend.agent.tools.rag import search_rag

TOOL_REGISTRY: dict[str, Callable] = {
    "poi_lookup": poi_lookup,
    "search_rag": search_rag,
    "get_plan": get_plan,
    "get_plan_result": get_plan_result,
}

__all__ = [
    "get_plan",
    "get_plan_result",
    "parse_biz_hours",
    "poi_lookup",
    "search_rag",
    "TOOL_REGISTRY",
]
