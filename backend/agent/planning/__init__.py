"""规划能力子包：方案调整操作（增删景点）+ 评语生成（agent-tool 待接入）。

消费方：engine/pipeline.py（adjust_plan 分发方案调整）；
generate_commentary 已从流程剥离（返回 commentary=None），待 Agent 工具化后接入。
子模块被 pipeline 延迟 import 调用（避免 engine → agent 顶层循环导入）。

结构：_core.py（公共内核）+ commentator.py（评语）留在包根；
调整操作（add_poi/remove_poi/balance）归入 ops/ 子包。
（adjust_days 已删除：改天数能力由 suggest 阶段多解列表天然覆盖，无需独立功能）
"""

from backend.agent.planning.commentator import generate_commentary
from backend.agent.planning.ops import (
    add_poi_to_day,
    add_poi_to_plan,
    balance_groups,
    remove_poi_from_day,
    remove_poi_from_plan,
)

__all__ = [
    "generate_commentary",
    "add_poi_to_day",
    "add_poi_to_plan",
    "balance_groups",
    "remove_poi_from_day",
    "remove_poi_from_plan",
]
