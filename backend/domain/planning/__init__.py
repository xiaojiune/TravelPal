"""行程调整子域：方案增删景点 + 重排（纯领域编排，零 IO）。

从 agent/planning 抽回 domain 的域编排逻辑——add/remove 方案调整本质是
OR 重排，只依赖 domain 求解接口 + solver_factory 注入，无 agent/LLM 依赖。
评语生成（commentator.generate_commentary）仍属 agent 层，见
backend/agent/planning/commentator.py。

公开符号：
- add_poi_to_day / add_poi_to_plan：添加景点重排（单日/全局）
- remove_poi_from_day / remove_poi_from_plan：移除景点重排（单日/全局）
- balance_groups：平衡分组（@placeholder 占位）
- extract_cores / reorder_from_cores：重排公共内核（reorder 需注入 solver_factory）
"""

from backend.domain.planning._core import extract_cores, reorder_from_cores
from backend.domain.planning.ops import (
    add_poi_to_day,
    add_poi_to_plan,
    balance_groups,
    remove_poi_from_day,
    remove_poi_from_plan,
)

__all__ = [
    "extract_cores",
    "reorder_from_cores",
    "add_poi_to_day",
    "add_poi_to_plan",
    "balance_groups",
    "remove_poi_from_day",
    "remove_poi_from_plan",
]
