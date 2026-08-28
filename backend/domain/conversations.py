"""会话域服务：Conversation 记录的业务逻辑（懒建、复用、历史读取、TTL 清理）。

轴6 会话/记忆地基：
- Conversation 表只存会话元数据（归属/标题/TTL），消息历史由 AsyncPostgresSaver
  持久化在 checkpoint 表（单一来源）。
- 会话归属规则：登录用户（user_id 非 None）会话持久、可跨刷新恢复（复用最近未过期
  会话）；游客（user_id None）会话每次新建、可被覆盖；归属不符时当作新会话（防串）。
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.chat.checkpointer import get_checkpointer
from backend.data.model.models import Conversation

# 会话 TTL：登录用户 7 天，匿名访客 1 天
TTL_LOGGED_IN = timedelta(days=7)
TTL_ANONYMOUS = timedelta(days=1)


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


async def get_or_create_conversation(
    session: AsyncSession,
    conversation_id: str | None,
    user_id: UUID | None,
) -> tuple[Conversation, bool]:
    """取会话；登录用户未带 id 时复用其最近未过期会话，游客每次新建。

    懒创建/复用：
    - 显式 conversation_id：取对应会话；归属不符当作新会话（防串）。
    - 登录用户（user_id 非 None）未带 id：复用其最近未过期会话（跨刷新恢复历史）。
    - 游客（user_id None）：每次新建（可被覆盖）。
    - 过期会话：清理 checkpoint + 本记录后当新会话。

    Args:
        session: 数据库会话。
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
        try:
            conv = await session.get(Conversation, UUID(conversation_id))
        except ValueError:
            conv = None
        if conv is not None and conv.expires_at <= now:  # pyright: ignore[reportGeneralTypeIssues]
            await _cleanup_conversation(conv)
            await session.delete(conv)
            await session.commit()
            conv = None
        elif conv is not None and not _belongs(conv.user_id, user_id):  # pyright: ignore[reportArgumentType]
            conv = None
    if conv is None and user_id is not None:
        # 登录用户：复用最近未过期会话（跨登录/刷新恢复上下文）
        conv = (
            await session.execute(
                select(Conversation)
                .where(Conversation.user_id == user_id, Conversation.expires_at > now)
                .order_by(Conversation.updated_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
    if conv is not None:
        return conv, False

    conv = Conversation(user_id=user_id, expires_at=_expires_for(user_id))
    session.add(conv)
    await session.commit()
    await session.refresh(conv)
    return conv, True


async def get_recent_conversation(
    session: AsyncSession,
    user_id: UUID | None,
) -> Conversation | None:
    """取该用户最近未过期会话（只查不建）；游客/无历史返回 None。

    与 get_or_create_conversation 同源查询，但**不创建**：供「查看/恢复历史」
    通道使用（打开 Agent 面板回显最近会话），避免只读访问也落库。

    Args:
        session: 数据库会话。
        user_id: 归属用户 UUID（未登录为 None）。

    Returns:
        Conversation | None: 最近未过期会话；游客或用户无历史时为 None。
    """
    if user_id is None:
        return None
    now = datetime.now(timezone.utc)
    return (
        await session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id, Conversation.expires_at > now)
            .order_by(Conversation.updated_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def get_history_messages(thread_id: str) -> list[dict]:
    """从 checkpoint 读取该线程的历史消息（dict 列表）；无历史返回空。

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


async def _cleanup_conversation(conv: Conversation) -> None:
    """清理过期会话：删 checkpoint 状态（记录删除由调用方处理）。

    Args:
        conv: 过期会话记录。
    """
    try:
        await get_checkpointer().adelete_thread(str(conv.id))
    except Exception:
        # checkpoint 清理失败不阻断（可能无状态/连接异常），仅尽力而为
        pass
