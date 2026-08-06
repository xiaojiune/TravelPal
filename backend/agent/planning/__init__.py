"""规划能力子包：评语生成 + 方案调整（改天数/增删景点重求解）。

消费方：engine/pipeline.py（run_planning 输出评语、adjust_plan 分发方案调整）。
planner 内的函数被 pipeline 延迟 import 调用（避免 engine → agent 顶层循环导入）。
"""

from backend.agent.planning.commentator import generate_commentary
from backend.agent.planning.planner import add_poi_to_plan, adjust_plan_days, remove_poi_from_plan

__all__ = [
    "generate_commentary",
    "add_poi_to_plan",
    "adjust_plan_days",
    "remove_poi_from_plan",
]
