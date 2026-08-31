"""会话领域纯规则 + 领域会话类型（值对象）。

会话承载用户历史/记忆的归属，属领域层；DB 存取归 infrastructure。
本模块只含与框架无关的规则与类型：
- ``Conversation``：领域会话类型（轻量，infra ORM 映射到它，domain 不碰 ORM）。
- ``TTL_LOGGED_IN``/``TTL_ANONYMOUS``/``_expires_for``/``_belongs``：归属与 TTL 规则。

domain 零外部实现依赖：只 import 标准库。
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

# 会话 TTL：登录用户 7 天，匿名访客 1 天（UTC aware）。
TTL_LOGGED_IN = timedelta(days=7)
TTL_ANONYMOUS = timedelta(days=1)


@dataclass(eq=False)  # eq=False → 保留对象身份哈希，可作字典键（infra 的 _pending 会话找回用）
class Conversation:
    """领域会话（轻量）：infra 的 ORM Conversation 映射到它。

    user_id 为归属用户（None=游客）；id 为会话主键（= LangGraph thread_id），
    新建会话在持久化前为 None（由 infra 落库后回填）。

    注：``eq=False`` 使其按「对象身份」比较/哈希（可作字典键），而非按字段值比较；
    字段比较（如 ``conv.id == x``）仍按需显式进行。
    """

    user_id: UUID | None
    expires_at: datetime
    id: UUID | None = None


def _expires_for(user_id: UUID | None) -> datetime:
    """按是否登录计算会话过期时间（登录 7 天/匿名 1 天，UTC aware）。"""
    delta = TTL_LOGGED_IN if user_id is not None else TTL_ANONYMOUS
    return datetime.now(timezone.utc) + delta


def _belongs(conv_user_id: UUID | None, current_user_id: UUID | None) -> bool:
    """会话归属判断：登录会话仅归登录用户；游客会话仅游客可用（防串会话）。

    Args:
        conv_user_id: 会话记录的归属用户（None=游客会话）。
        current_user_id: 当前请求的归属用户（None=游客）。

    Returns:
        bool: 当前用户是否可访问该会话。
    """
    if conv_user_id is None:
        return current_user_id is None
    return conv_user_id == current_user_id
