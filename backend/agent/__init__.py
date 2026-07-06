# ================== 接口清单 ==================
#
# ---- tools.py ----
# parse_biz_hours(opentime2) -> tuple[int, int] | None         LLM 解析高德 opentime2 营业时间为 (start_min, end_min)
# build_chat_messages(message, plan_result) -> list[dict]      构建对话消息列表
# chat_stream(messages) -> Generator[str]                      SSE 流式聊天（Mock 或 DeepSeek）
#
# ---- commentator.py ----
# generate_commentary(solution, spots, dist_mat) -> str        规则模板生成规划评语

from backend.agent.tools import parse_biz_hours, build_chat_messages, chat_stream
from backend.agent.commentator import generate_commentary

__all__ = ["parse_biz_hours", "build_chat_messages", "chat_stream", "generate_commentary"]
