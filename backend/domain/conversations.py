"""会话域服务：Conversation 记录的业务逻辑（懒建、历史读取、TTL 清理）。

轴6 会话/记忆地基：
- Conversation 表只存会话元数据（归属/标题/TTL），消息历史由 AsyncPostgresSaver
  持久化在 checkpoint 表（单一来源）。
- 本模块负责会话表的创建/复用/过期处理，并以 checkpointer 读取/清理消息历史。
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID

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


async def get_or_create_conversation(
    session: AsyncSession,
    conversation_id: str | None,
    user_id: UUID | None,
) -> tuple[Conversation, bool]:
    """取指定会话；不存在/已过期/非法 id 则新建。

    懒创建：前端首条消息带空 conversation_id 时在此新建，返回新会话与 created=True。

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
            # 懒清理：会话已过期 → 删 checkpoint 状态 + 本记录，作为新会话
            await _cleanup_conversation(conv)
            await session.delete(conv)
            await session.commit()
            conv = None
    if conv is not None:
        return conv, False

    conv = Conversation(user_id=user_id, expires_at=_expires_for(user_id))
    session.add(conv)
    await session.commit()
    await session.refresh(conv)
    return conv, True


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
