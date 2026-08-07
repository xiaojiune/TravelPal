"""规划能力子包：评语生成 + 方案调整操作（改天数/增删景点）。

消费方：engine/pipeline.py（run_planning 输出评语、adjust_plan 分发方案调整）。
子模块被 pipeline 延迟 import 调用（避免 engine → agent 顶层循环导入）。

结构：_core.py（公共内核）+ commentator.py（评语）留在包根；
四个调整操作（add_poi/remove_poi/adjust_days/balance）归入 ops/ 子包。
"""

from backend.agent.planning.commentator import generate_commentary
from backend.agent.planning.ops import (
    add_poi_to_day,
    add_poi_to_plan,
    adjust_plan_days,
    balance_groups,
    remove_poi_from_day,
    remove_poi_from_plan,
)

__all__ = [
    "generate_commentary",
    "add_poi_to_day",
    "add_poi_to_plan",
    "adjust_plan_days",
    "balance_groups",
    "remove_poi_from_day",
    "remove_poi_from_plan",
]
