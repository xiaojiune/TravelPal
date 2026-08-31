"""会话领域：会话服务端口 + 会话存储端口 + 纯业务规则。

会话承载用户历史/记忆的归属，属领域层；但 DB 存取（Conversation 表、
LangGraph checkpoint）归 infrastructure。本模块只定义：

- ``Conversation``：领域会话类型（轻量，infra ORM 映射到它，domain 不碰 ORM）。
- ``ConversationSession``：会话存储端口（抽象会话表的域操作集，隔离 sqlalchemy）。
- ``ConversationStore``：会话服务端口（上层 get_or_create/get_recent/get_history）。
- ``_belongs``/``_expires_for``/TTL：纯业务规则。

domain 零外部实现依赖：只 import 标准库，具体存取由 infrastructure 实现。
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol
from uuid import UUID

# 会话 TTL：登录用户 7 天，匿名访客 1 天（UTC aware）。
TTL_LOGGED_IN = timedelta(days=7)
TTL_ANONYMOUS = timedelta(days=1)


@dataclass
class Conversation:
    """领域会话（轻量）：infra 的 ORM Conversation 映射到它。

    user_id 为归属用户（None=游客）；id 为会话主键（= LangGraph thread_id），
    新建会话在持久化前为 None（由 infra 落库后回填）。
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


class ConversationSession(Protocol):
    """会话存储端口：抽象会话表的域操作集（domain 不碰 sqlalchemy）。

    infra 提供一个 Adapter，由 `AsyncSession` 满足本协议（把 ORM 存取
    映射到 ``Conversation``）。domain 端只调用这些域级方法。
    """

    async def get(self, conversation_id: UUID) -> Conversation | None:
        """按 id 取会话记录（不存在返回 None）。"""
        ...

    async def find_recent(self, user_id: UUID | None) -> Conversation | None:
        """取该用户最近未过期会话（只查不建）；游客/无历史返回 None。"""
        ...

    def add(self, conversation: Conversation) -> None:
        """登记新会话（未提交前仅标记，由 commit 落库）。"""
        ...

    async def delete(self, conversation: Conversation) -> None:
        """标记删除会话（uncommit 由 commit 生效）。"""
        ...

    async def commit(self) -> None:
        """提交当前会话上下文内未落库的变更。"""
        ...

    async def refresh(self, conversation: Conversation) -> None:
        """从库刷新会话对象状态（取生成的主键等）。"""
        ...


class ConversationStore(Protocol):
    """会话服务端口：上层（api/agent）取会话、建会话、读历史。

    实现由 infrastructure 提供（PostgresConversationStore）——会话存取的
    DB 细节（Conversation 表 + checkpoint）都在实现侧。
    """

    async def get_or_create(
        self,
        session: ConversationSession,
        conversation_id: str | None,
        user_id: UUID | None,
    ) -> tuple[Conversation, bool]:
        """取会话；登录用户未带 id 时复用其最近未过期会话，游客每次新建。

        Returns:
            (会话, created=是否新建)。
        """
        ...

    async def get_recent(
        self,
        session: ConversationSession,
        user_id: UUID | None,
    ) -> Conversation | None:
        """取该用户最近未过期会话（只查不建）；游客/无历史返回 None。"""
        ...

    async def get_history_messages(self, thread_id: str) -> list[dict]:
        """从 checkpoint 读该线程历史消息（dict 列表）；无历史返回空。"""
        ...
