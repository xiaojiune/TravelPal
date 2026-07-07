# ================== 接口清单 ==================
#
# ---- tools.py ----
# parse_biz_hours(opentime2) -> tuple[int, int] | None         LLM 解析高德 opentime2 营业时间为 (start_min, end_min)
# build_chat_messages(message, plan_result) -> list[dict]      构建对话消息列表
# chat_stream(messages) -> Generator[str]                      SSE 流式聊天（Mock 或 DeepSeek）
#
# ---- commentator.py ----
# generate_commentary(solution, spots, dist_mat) -> str        规则模板生成规划评语
#
# ---- planner.py ----
# adjust_plan_days(spots_dict, cost_matrix, dist_matrix, new_n_days) -> dict  调整方案天数并重新规划
# remove_poi_from_plan(spots_dict, cost_matrix, dist_matrix, routes, poi_name) -> dict  从方案中移除景点并重新求解

from backend.agent.tools import parse_biz_hours, build_chat_messages, chat_stream
from backend.agent.commentator import generate_commentary
from backend.agent.planner import adjust_plan_days, remove_poi_from_plan

__all__ = ["parse_biz_hours", "build_chat_messages", "chat_stream", "generate_commentary",
           "adjust_plan_days", "remove_poi_from_plan"]
