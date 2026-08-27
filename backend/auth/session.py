"""服务端会话管理（httpOnly Cookie + Redis Session）。

- 会话键：tp:session:{session_id} → user_id（str）。
- session_id 用 secrets.token_urlsafe(32) 生成，不可猜测。
- TTL：settings.SESSION_TTL_SECONDS（默认 7 天）。
- 语义：Redis 不可用时对认证 fail-closed——get_session 返回 None（视为未登录），
  不放行；create_session 返回 None（登录失败）。
"""
import secrets
from typing import Any

from backend.config import settings

_SESSION_PREFIX = "tp:session:"

_client: Any | None = None


def _get_redis() -> Any | None:
    """懒初始化同步 Redis 客户端（与 driving_cache 一致，decode_responses=True）。

    Returns:
        redis.Redis | None: 客户端；连接失败返回 None。
    """
    global _client
    if _client is None:
        try:
            import redis  # 延迟导入：避免非认证路径引入 redis 依赖

            _client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        except Exception:
            _client = None
    return _client


def _key(session_id: str) -> str:
    """构造会话 Redis 键。"""
    return f"{_SESSION_PREFIX}{session_id}"


def create_session(user_id: str) -> str | None:
    """创建会话，返回 session_id；Redis 不可用时返回 None。

    Args:
        user_id: 归属用户 UUID 字符串。

    Returns:
        str | None: session_id；失败返回 None。
    """
    client = _get_redis()
    if client is None:
        return None
    try:
        session_id = secrets.token_urlsafe(32)
        client.set(_key(session_id), user_id, ex=settings.SESSION_TTL_SECONDS)
        return session_id
    except Exception:
        return None


def get_session(session_id: str | None) -> str | None:
    """按 session_id 取 user_id；无/失效/Redis 不可用返回 None（fail-closed）。

    Args:
        session_id: Cookie 中的会话标识。

    Returns:
        str | None: 归属 user_id；未登录返回 None。
    """
    if not session_id:
        return None
    client = _get_redis()
    if client is None:
        return None
    try:
        return client.get(_key(session_id))
    except Exception:
        return None


def revoke_session(session_id: str | None) -> None:
    """撤销会话（登出）。

    Args:
        session_id: 会话标识。
    """
    if not session_id:
        return
    client = _get_redis()
    if client is None:
        return
    try:
        client.delete(_key(session_id))
    except Exception:
        pass
