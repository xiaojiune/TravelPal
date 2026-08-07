"""工具包：Agent 可调用的工具函数合集与注册表。

按 TOOL_CATEGORIES 分组为子包（poi / plan / rag / driving）：
- poi/   ：查询类（poi_lookup + parse_biz_hours + estimate_stay）
- plan/  ：规划类（get_plan / get_plan_result / add_poi / remove_poi）
- rag/   ：检索类（search_rag）
- driving：路径类（get_driving）

schema.py 为工具契约生成器（build_tool_definitions），供编排器/MCP 共用。
"""

from collections.abc import Callable

from backend.agent.tools.driving import get_driving
from backend.agent.tools.plan import add_poi, get_plan, get_plan_result, remove_poi
from backend.agent.tools.poi import parse_biz_hours, poi_lookup
from backend.agent.tools.rag import search_rag

TOOL_REGISTRY: dict[str, Callable] = {
    "poi_lookup": poi_lookup,
    "search_rag": search_rag,
    "get_plan": get_plan,
    "get_plan_result": get_plan_result,
    "get_driving": get_driving,
    "add_poi": add_poi,
    "remove_poi": remove_poi,
}

# 工具分组元数据（方案 B 平行映射）：TOOL_REGISTRY 保持纯注册表，分类独立维护。
# 消费者（编排器工具裁剪 / 未来 MCP 分组 / Agent-driven UI 表单渲染）读本表零侵入。
# 子包目录结构与本表一一对应（poi/plan/rag/driving）。
# 方案 A（TOOL_REGISTRY 结构化 {fn, category}）在 category 成为一等公民时再合并，
# 当前避免波及 MCP server.py 与编排器分发层。
TOOL_CATEGORIES: dict[str, str] = {
    "poi_lookup": "poi",
    "search_rag": "rag",
    "get_plan": "plan",
    "get_plan_result": "plan",
    "get_driving": "driving",
    "add_poi": "plan",
    "remove_poi": "plan",
}

__all__ = [
    "get_driving",
    "add_poi",
    "get_plan",
    "get_plan_result",
    "remove_poi",
    "parse_biz_hours",
    "poi_lookup",
    "search_rag",
    "TOOL_REGISTRY",
    "TOOL_CATEGORIES",
]
