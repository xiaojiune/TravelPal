"""会话服务实现（Postgres）：Conversation 表 + LangGraph checkpoint 存取。

implements 会话端口（backend/domain/conversations.py）：
- ``SqlAlchemyConversationSession``：AsyncSession → ConversationSession 适配（ORM↔domain 映射）。
- ``PostgresConversationStore``：implements ConversationStore（会话建/取/历史）。

领域规则（归属/TTL）复用 domain（_belongs/_expires_for），本文件只做存取实现。
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.conversations import (
    Conversation,
    ConversationSession,
    ConversationStore,
    _belongs,
    _expires_for,
)
from backend.infrastructure.db.checkpointer import get_checkpointer
from backend.infrastructure.db.models import Conversation as ORMConversation

__all__ = ["SqlAlchemyConversationSession", "PostgresConversationStore"]


class SqlAlchemyConversationSession:
    """把一个 AsyncSession 适配成 ConversationSession（隔离 sqlalchemy）。

    负责 ORM Conversation ↔ domain Conversation 的映射，以及新建会话的 id 回填。
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._pending: dict[Conversation, ORMConversation] = {}

    @staticmethod
    def _to_domain(orm: ORMConversation) -> Conversation:
        return Conversation(user_id=orm.user_id, expires_at=orm.expires_at, id=orm.id)  # type: ignore[arg-type]

    async def get(self, conversation_id: UUID) -> Conversation | None:
        orm = await self._session.get(ORMConversation, conversation_id)
        return self._to_domain(orm) if orm is not None else None

    async def find_recent(self, user_id: UUID | None) -> Conversation | None:
        if user_id is None:
            return None
        now = datetime.now(timezone.utc)
        orm = (
            await self._session.execute(
                select(ORMConversation)
                .where(ORMConversation.user_id == user_id, ORMConversation.expires_at > now)
                .order_by(ORMConversation.updated_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        return self._to_domain(orm) if orm is not None else None

    def add(self, conversation: Conversation) -> None:
        orm = ORMConversation(user_id=conversation.user_id, expires_at=conversation.expires_at)
        self._session.add(orm)
        self._pending[conversation] = orm

    async def delete(self, conversation: Conversation) -> None:
        if conversation.id is None:
            return
        orm = await self._session.get(ORMConversation, conversation.id)
        if orm is not None:
            await self._session.delete(orm)

    async def commit(self) -> None:
        await self._session.commit()

    async def refresh(self, conversation: Conversation) -> None:
        orm = self._pending.get(conversation)
        if orm is not None:
            await self._session.refresh(orm)
            conversation.id = orm.id


class PostgresConversationStore:
    """implements ConversationStore：Conversation 表 + checkpoint 的存取实现。"""

    async def _cleanup_checkpoint(self, conversation: Conversation) -> None:
        if conversation.id is None:
            return
        try:
            await get_checkpointer().adelete_thread(str(conversation.id))
        except Exception:
            # checkpoint 清理失败不阻断（可能无状态/连接异常），仅尽力而为
            pass

    async def get_or_create(
        self,
        session: ConversationSession,
        conversation_id: str | None,
        user_id: UUID | None,
    ) -> tuple[Conversation, bool]:
        now = datetime.now(timezone.utc)
        conv = None
        if conversation_id:
            try:
                conv = await session.get(UUID(conversation_id))
            except ValueError:
                conv = None
            if conv is not None and conv.expires_at <= now:
                await self._cleanup_checkpoint(conv)
                await session.delete(conv)
                await session.commit()
                conv = None
            elif conv is not None and not _belongs(conv.user_id, user_id):
                conv = None
        if conv is None and user_id is not None:
            conv = await session.find_recent(user_id)
        if conv is not None:
            return conv, False
        conv = Conversation(user_id=user_id, expires_at=_expires_for(user_id))
        session.add(conv)
        await session.commit()
        await session.refresh(conv)
        return conv, True

    async def get_recent(
        self,
        session: ConversationSession,
        user_id: UUID | None,
    ) -> Conversation | None:
        return await session.find_recent(user_id)

    async def get_history_messages(self, thread_id: str) -> list[dict]:
        checkpointer = get_checkpointer()
        cp = await checkpointer.aget({"configurable": {"thread_id": thread_id}})
        if cp is not None and isinstance(cp, dict):
            return list(cp.get("channel_values", {}).get("messages", []))
        return []
