"""规划能力子包：评语生成 + 方案调整（改天数/增删景点重求解）。

消费方：engine/pipeline.py（run_planning 输出评语、adjust_plan 分发方案调整）。
子模块被 pipeline 延迟 import 调用（避免 engine → agent 顶层循环导入）。
"""

from backend.agent.planning.add_poi import add_poi_to_plan
from backend.agent.planning.adjust_days import adjust_plan_days
from backend.agent.planning.commentator import generate_commentary
from backend.agent.planning.remove_poi import remove_poi_from_plan

__all__ = [
    "add_poi_to_plan",
    "adjust_plan_days",
    "generate_commentary",
    "remove_poi_from_plan",
]
