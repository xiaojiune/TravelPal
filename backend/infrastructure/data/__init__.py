"""数据层（暂存）：会话域服务（conversations）。

ORM 与外部 API 已分别归 infrastructure/db/ 与 infrastructure/external/amap/；
本层暂存会话服务，待后续单独收敛上移 domain（会话属领域层）。
"""

from backend.infrastructure.data.conversations import (
    get_history_messages,
    get_or_create_conversation,
    get_recent_conversation,
)

__all__ = [
    "get_history_messages",
    "get_or_create_conversation",
    "get_recent_conversation",
]
