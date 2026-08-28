"""轴6 会话/记忆契约测试：ChatRequest.conversation_id、会话 TTL、checkpointer URL。

纯单元，不连 DB/Redis；覆盖会话记忆的基础契约（schemas 字段 + 域常量 + URL 归一化）。
"""
from uuid import uuid4

from backend.agent.chat.checkpointer import psycopg_url
from backend.api.schemas import ChatRequest
from backend.domain.conversations import TTL_ANONYMOUS, TTL_LOGGED_IN, _expires_for


class TestChatRequestConversationId:
    """对话请求的 conversation_id 契约（首条为空懒建，后续携带续接）。"""

    def test_conversation_id_optional(self):
        req = ChatRequest(message="hi")
        assert req.conversation_id is None

    def test_conversation_id_accepted(self):
        req = ChatRequest(message="hi", conversation_id="abc-123")
        assert req.conversation_id == "abc-123"


class TestConversationTTL:
    """会话 TTL：登录 7 天 / 匿名 1 天；_expires_for 返回 future aware 时间。"""

    def test_logged_in_ttl_is_7_days(self):
        assert TTL_LOGGED_IN.days == 7

    def test_anonymous_ttl_is_1_day(self):
        assert TTL_ANONYMOUS.days == 1

    def test_expires_for_gives_future(self):
        from datetime import datetime, timezone

        expires = _expires_for(uuid4())
        assert expires.tzinfo is not None
        assert expires > datetime.now(timezone.utc)


class TestCheckpointerUrl:
    """checkpointer 用 psycopg 异步连接：URL 去掉 asyncpg 后缀。"""

    def test_psycopg_url_strips_asyncpg(self):
        url = psycopg_url()
        assert url.startswith("postgresql://")
        assert "+asyncpg" not in url
