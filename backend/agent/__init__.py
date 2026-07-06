# ================== 接口清单 ==================
#
# ---- tools.py ----
# parse_biz_hours(opentime2) -> tuple[int, int] | None     LLM 解析高德 opentime2 营业时间为 (start_min, end_min)
#
# ---- commentator.py ----
# generate_commentary(solution, spots, dist_mat) -> str    规则模板生成规划评语

from backend.agent.tools import parse_biz_hours
from backend.agent.commentator import generate_commentary

__all__ = ["parse_biz_hours", "generate_commentary"]
