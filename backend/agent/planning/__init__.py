"""规划能力子包：评语生成（agent 层）。

方案调整的域编排逻辑已抽回 backend/domain/planning/（add/remove 重排），
此处仅保留面向 Agent 的评语生成（generate_commentary，当前返回 commentary=None，
待 Agent 工具化后接入）。
"""

from backend.agent.planning.commentator import generate_commentary

__all__ = ["generate_commentary"]
