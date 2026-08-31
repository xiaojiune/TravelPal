"""会话服务实现（Postgres）：Conversation 表 + LangGraph checkpoint 存取。

implements 会话端口（backend/domain/conversations.py）：
- ``SqlAlchemyConversationSession``：AsyncSession → ``ConversationSession`` 的适配器
  （负责 ORM ``Conversation`` ↔ domain ``Conversation`` 的映射、新建会话 id 回填）。
- ``PostgresConversationStore``：implements ``ConversationStore``（会话建/取/历史读取）。

轴6 会话/记忆地基（与旧域服务一致）：
- ``Conversation`` 表只存会话**元数据**（归属 user_id / TTL / 标题），消息历史由
  LangGraph 的 AsyncPostgresSaver 持久化在 **checkpoint** 表（单一来源，见
  ``db/checkpointer.py``）。
- 归属规则：登录用户（user_id 非 None）会话持久、可跨刷新恢复（复用最近未过期会话）；
  游客（user_id None）会话每次新建、可被覆盖；归属不符时当作新会话（防串）。

领域规则（归属/TTL）复用 domain（``_belongs``/``_expires_for``），本文件只做存取实现。
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
    """把一个 AsyncSession 适配成 ``ConversationSession``（隔离 sqlalchemy）。

    作用是让 domain 端只依赖抽象会话端口、不感知 ORM：把 ``AsyncSession`` 的
    ORM ``Conversation`` 存取映射成 domain ``Conversation``，并把新建时未生成的
    主键（id）在落库/refresh 后回填到 domain 对象。

    生命周期：按请求构造（一个请求一个实例），随 ``AsyncSession`` 一起结束。
    """

    def __init__(self, session: AsyncSession) -> None:
        # _pending 记录「尚未落库的新建会话」→ 其对应的 ORM 对象，
        # 供 refresh 时回填 domain Conversation.id（ORM 主键由数据库生成）。
        self._session = session
        self._pending: dict[Conversation, ORMConversation] = {}

    @staticmethod
    def _to_domain(orm: ORMConversation) -> Conversation:
        """ORM Conversation → domain Conversation（丢弃 ORM 专属字段）。"""
        return Conversation(user_id=orm.user_id, expires_at=orm.expires_at, id=orm.id)  # type: ignore[arg-type]

    async def get(self, conversation_id: UUID) -> Conversation | None:
        """按 id 取会话记录（不存在返回 None）。

        Args:
            conversation_id: 会话主键（UUID）。

        Returns:
            domain ``Conversation`` 或 None。
        """
        orm = await self._session.get(ORMConversation, conversation_id)
        return self._to_domain(orm) if orm is not None else None

    async def find_recent(self, user_id: UUID | None) -> Conversation | None:
        """取该用户最近未过期会话（只查不建）；游客/无历史返回 None。

        Args:
            user_id: 归属用户 UUID（未登录为 None，直接返回 None）。

        Returns:
            domain ``Conversation`` 或 None（游客或用户无历史时）。
        """
        if user_id is None:
            return None
        now = datetime.now(timezone.utc)
        # 只在未过期的会话中取最近更新的那条（updated_at 倒序）。
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
        """登记新会话为"待落库"（此时 id 尚未生成，由 commit 落库、refresh 回填）。

        Args:
            conversation: 新建的 domain ``Conversation``（id 为 None）。
        """
        orm = ORMConversation(user_id=conversation.user_id, expires_at=conversation.expires_at)
        self._session.add(orm)
        # 记住 domain ↔ orm 对应，供 refresh 回填主键。
        self._pending[conversation] = orm

    async def delete(self, conversation: Conversation) -> None:
        """按 id 标记删除会话（未提交前不落库，由 commit 生效）。

        Args:
            conversation: 待删除会话（id 须有效，否则 no-op）。
        """
        if conversation.id is None:
            return
        orm = await self._session.get(ORMConversation, conversation.id)
        if orm is not None:
            await self._session.delete(orm)

    async def commit(self) -> None:
        """提交当前会话上下文内未落库的变更（add/delete 生效）。"""
        await self._session.commit()

    async def refresh(self, conversation: Conversation) -> None:
        """落库后回填新建会话的主键（id）。

        Args:
            conversation: 先前经 ``add`` 登记的新建会话。
        """
        orm = self._pending.get(conversation)
        if orm is not None:
            await self._session.refresh(orm)
            conversation.id = orm.id


class PostgresConversationStore:
    """implements ``ConversationStore``：Conversation 表 + checkpoint 的存取实现。

    会话建/取走注入的 ``ConversationSession``（按请求的 AsyncSession 适配），
    历史读取直接走 checkpoint；本 store 无请求级状态，可作单例复用。
    """

    async def _cleanup_checkpoint(self, conversation: Conversation) -> None:
        """清理过期会话的 checkpoint 状态（记录删除由调用方处理）。

        注意：checkpoint 清理失败**不阻断**（可能无状态/连接异常），仅尽力而为，
        避免因清理失败阻塞会话过期重建。
        """
        if conversation.id is None:
            return
        try:
            await get_checkpointer().adelete_thread(str(conversation.id))
        except Exception:
            # 尽力而为：清理失败不抛，保留会话过期重建路径。
            pass

    async def get_or_create(
        self,
        session: ConversationSession,
        conversation_id: str | None,
        user_id: UUID | None,
    ) -> tuple[Conversation, bool]:
        """取会话；登录用户未带 id 时复用其最近未过期会话，游客每次新建。

        懒创建/复用（与旧域服务 `get_or_create_conversation` 同语义）：
        - 显式 ``conversation_id``：取对应会话；过期则清理 checkpoint + 记录后当新会话；
          归属不符当作新会话（防串）。
        - 登录用户（user_id 非 None）未带 id：复用其最近未过期会话（跨刷新恢复历史）。
        - 游客（user_id None）：每次新建（可被覆盖）。
        - 过期会话：清理 checkpoint + 本记录后当新会话。

        Args:
            session: 会话存储端口（按请求的 AsyncSession 适配）。
            conversation_id: 前端传入的会话 id（可为空/非法）。
            user_id: 归属用户 UUID（未登录为 None）。

        Returns:
            tuple[Conversation, bool]: (会话记录, created=是否新建)。

        Raises:
            Exception: 数据库写入失败时向上抛出，由调用方处理。
        """
        now = datetime.now(timezone.utc)
        conv = None
        if conversation_id:
            # 显式 id：取对应会话；非法 id 视为无会话（走新建/复用）。
            try:
                conv = await session.get(UUID(conversation_id))
            except ValueError:
                conv = None
            if conv is not None and conv.expires_at <= now:
                # 过期会话：清 checkpoint + 删记录，当作新会话重建。
                await self._cleanup_checkpoint(conv)
                await session.delete(conv)
                await session.commit()
                conv = None
            elif conv is not None and not _belongs(conv.user_id, user_id):
                # 归属不符（防串）：当作新会话，不沿用旧的。
                conv = None
        if conv is None and user_id is not None:
            # 登录用户未带 id：复用最近未过期会话（跨登录/刷新恢复上下文）。
            conv = await session.find_recent(user_id)
        if conv is not None:
            return conv, False
        # 无可用会话 → 新建；落库后由 refresh 回填主键 id。
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
        """取该用户最近未过期会话（只查不建）；游客/无历史返回 None。

        与 ``get_or_create`` 同源查询但**不创建**：供「查看/恢复历史」通道使用
        （打开 Agent 面板回显最近会话），避免只读访问也落库。

        Args:
            session: 会话存储端口。
            user_id: 归属用户 UUID（未登录为 None）。

        Returns:
            domain ``Conversation`` 或 None（游客或用户无历史时）。
        """
        return await session.find_recent(user_id)

    async def get_history_messages(self, thread_id: str) -> list[dict]:
        """从 checkpoint 读取该线程的历史消息（dict 列表）；无历史返回空。

        供续接上下文：把上一轮消息拼进本轮 prompt（会话记忆方案 B——历史由
        orchestrator 读 checkpoint 后拼接，不做 add_messages 转换）。

        Args:
            thread_id: 会话线程 id（= conversation id）。

        Returns:
            list[dict]: OpenAI 兼容消息历史；无 checkpoint 时返回空列表。
        """
        checkpointer = get_checkpointer()
        cp = await checkpointer.aget({"configurable": {"thread_id": thread_id}})
        if cp is not None and isinstance(cp, dict):
            return list(cp.get("channel_values", {}).get("messages", []))
        return []
