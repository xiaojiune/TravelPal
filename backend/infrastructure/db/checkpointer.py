"""LangGraph 会话状态 checkpointer：AsyncPostgresSaver 的全局存取与生命周期管理。

轴6 会话/记忆地基：对话状态（含消息历史）由 AsyncPostgresSaver 持久化到
Postgres 的 checkpoint 表（框架内部表，由 setup() 幂等创建，不入 Alembic）。
本模块只做三件事：URL 转换、全局 saver 存取、lifespan 上下文。

注意：from_conn_string 建立单个 psycopg AsyncConnection（autocommit），
对话 SSE 一次一个长请求、并发低，先以单连接落地；后续若对话并发明显，
再换 AsyncConnectionPool（改动收敛在本模块）。
"""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from backend.config import settings

_saver: AsyncPostgresSaver | None = None


def psycopg_url() -> str:
    """将 asyncpg URL 转为 psycopg（AsyncPostgresSaver 用 psycopg async 连接）。

    Returns:
        str: 去掉 `+asyncpg` 后缀的 Postgres URL。
    """
    return settings.DATABASE_URL.replace("+asyncpg", "")


def get_checkpointer() -> AsyncPostgresSaver:
    """取全局 AsyncPostgresSaver 实例（须在 lifespan 启动后调用）。

    Returns:
        AsyncPostgresSaver: 会话状态持久化器。

    Raises:
        RuntimeError: lifespan 尚未 init（saver 未就绪）。
    """
    if _saver is None:
        raise RuntimeError("checkpointer 未初始化：应在 FastAPI lifespan 启动时 init")
    return _saver


@asynccontextmanager
async def checkpointer_context() -> AsyncIterator[AsyncPostgresSaver]:
    """lifespan 生命周期内持有 AsyncPostgresSaver，并幂等建 checkpoint 表。

    Yields:
        AsyncPostgresSaver: 生命周期内有效的 saver；lifespan 退出时自动关闭连接。
    """
    global _saver
    async with AsyncPostgresSaver.from_conn_string(psycopg_url()) as saver:
        await saver.setup()  # 幂等创建 checkpoint 表
        _saver = saver
        try:
            yield saver
        finally:
            _saver = None
