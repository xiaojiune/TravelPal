"""轴6 会话/记忆契约测试：ChatRequest.conversation_id、会话 TTL、checkpointer URL。

纯单元，不连 DB/Redis；覆盖会话记忆的基础契约（schemas 字段 + 域常量 + URL 归一化）。
"""
from uuid import uuid4

from backend.infrastructure.db.checkpointer import psycopg_url
from backend.api.schemas import ChatRequest
from backend.infrastructure.data.conversations import TTL_ANONYMOUS, TTL_LOGGED_IN, _belongs, _expires_for


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


class TestConversationBelongs:
    """会话归属判断：登录会话仅登录用户可用，游客会话仅游客可用（防串）。"""

    def test_guest_accesses_guest_conv(self):
        assert _belongs(conv_user_id=None, current_user_id=None) is True

    def test_guest_cannot_access_logged_conv(self):
        assert _belongs(conv_user_id=uuid4(), current_user_id=None) is False

    def test_user_accesses_own_conv(self):
        uid = uuid4()
        assert _belongs(conv_user_id=uid, current_user_id=uid) is True

    def test_user_cannot_access_other_user_conv(self):
        assert _belongs(conv_user_id=uuid4(), current_user_id=uuid4()) is False

    def test_user_cannot_access_guest_conv(self):
        assert _belongs(conv_user_id=None, current_user_id=uuid4()) is False
