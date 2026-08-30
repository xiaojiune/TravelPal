"""认证契约测试：密码哈希 + 认证 schemas + 鉴权依赖（纯单元，无 DB/Redis）。

覆盖轴1：bcrypt 校验行为；AuthRegister/AuthLogin/UserOut 请求/响应契约。
覆盖轴3：get_current_user_optional（无会话返回 None）、require_admin（RBAC 校验）。
"""
import asyncio
import uuid

from fastapi import HTTPException
import pytest
from starlette.requests import Request

from backend.api.auth import get_current_user_optional, require_admin
from backend.api.schemas import AuthLogin, AuthRegister, UserOut
from backend.domain.security import hash_password, verify_password
from backend.infrastructure.data.model.models import User


class TestPassword:
    """密码哈希/校验行为。"""

    def test_hash_bcrypt_prefix(self):
        assert hash_password("pw123456").startswith("$2b$")

    def test_verify_match(self):
        h = hash_password("pw123456")
        assert verify_password("pw123456", h) is True

    def test_verify_mismatch(self):
        h = hash_password("pw123456")
        assert verify_password("wrong", h) is False

    def test_verify_bad_hash(self):
        assert verify_password("pw123456", "not-a-bcrypt-hash") is False


class TestAuthRegisterContract:
    """注册请求契约。"""

    def test_email_min_length(self):
        with pytest.raises(ValueError):
            AuthRegister(email="ab", password="pw123456")  # email < 3

    def test_password_min_length(self):
        with pytest.raises(ValueError):
            AuthRegister(email="a@b.com", password="12345")  # password < 6

    def test_nickname_optional(self):
        req = AuthRegister(email="a@b.com", password="pw123456")
        assert req.nickname is None


class TestAuthLoginContract:
    """登录请求契约。"""

    def test_fields(self):
        req = AuthLogin(email="a@b.com", password="pw123456")
        assert req.email == "a@b.com"
        assert req.password == "pw123456"


class TestUserOutContract:
    """当前用户响应契约。"""

    def test_shape(self):
        user = UserOut(id="u1", email="a@b.com", nickname="张三", role="user", is_active=True)
        assert user.role == "user"
        assert user.is_active is True

    def test_optional_fields_nullable(self):
        user = UserOut(id="u1", email=None, nickname=None, role="guest", is_active=False)
        assert user.email is None
        assert user.nickname is None
        assert user.role == "guest"


def _no_cookie_request() -> Request:
    """构造不携带任何 Cookie 的 ASGI 请求，用于测试可选鉴权依赖。"""
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 80),
            "client": ("127.0.0.1", 1234),
            "scheme": "http",
            "root_path": "",
        }
    )


class TestAuthzDeps:
    """轴3 鉴权依赖契约：可选鉴权 + admin 校验（纯单元，不触 DB/Redis）。"""

    def test_optional_no_cookie_returns_none(self):
        """无 Cookie 时 get_current_user_optional 返回 None（全程不触 DB/Redis）。"""
        user = asyncio.run(get_current_user_optional(_no_cookie_request(), session=None))
        assert user is None

    def test_require_admin_passes_for_admin(self):
        """admin 角色通过 require_admin，返回当前用户。"""
        admin = User(id=uuid.uuid4(), role="admin", is_active=True)
        assert asyncio.run(require_admin(current=admin)) is admin

    def test_require_admin_passes_for_super_admin(self):
        """super_admin 角色同样通过 require_admin（后端管理 API 对两者就绪）。"""
        sa = User(id=uuid.uuid4(), role="super_admin", is_active=True)
        assert asyncio.run(require_admin(current=sa)) is sa

    def test_require_admin_rejects_non_admin(self):
        """非 admin 角色触发 403。"""
        user = User(id=uuid.uuid4(), role="user", is_active=True)
        with pytest.raises(HTTPException) as exc:
            asyncio.run(require_admin(current=user))
        assert exc.value.status_code == 403
