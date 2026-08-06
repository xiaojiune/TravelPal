"""工具包：Agent 可调用的工具函数合集与注册表。"""

from collections.abc import Callable

from backend.agent.tools.adjust import add_poi
from backend.agent.tools.driving import get_driving
from backend.agent.tools.plan import get_plan, get_plan_result
from backend.agent.tools.poi import parse_biz_hours, poi_lookup
from backend.agent.tools.rag import search_rag

TOOL_REGISTRY: dict[str, Callable] = {
    "poi_lookup": poi_lookup,
    "search_rag": search_rag,
    "get_plan": get_plan,
    "get_plan_result": get_plan_result,
    "get_driving": get_driving,
    "add_poi": add_poi,
}

# 工具分组元数据（方案 B 平行映射）：TOOL_REGISTRY 保持纯注册表，分类独立维护。
# 消费者（编排器工具裁剪 / 未来 MCP 分组 / Agent-driven UI 表单渲染）读本表零侵入。
# 方案 A（TOOL_REGISTRY 结构化 {fn, category}）在 category 成为一等公民时再合并，
# 当前避免波及 MCP server.py 与编排器分发层。
TOOL_CATEGORIES: dict[str, str] = {
    "poi_lookup": "poi",
    "search_rag": "rag",
    "get_plan": "planning",
    "get_plan_result": "planning",
    "get_driving": "driving",
    "add_poi": "planning",
}

__all__ = [
    "add_poi",
    "get_driving",
    "get_plan",
    "get_plan_result",
    "parse_biz_hours",
    "poi_lookup",
    "search_rag",
    "TOOL_REGISTRY",
    "TOOL_CATEGORIES",
]
