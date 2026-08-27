"""认证契约测试：密码哈希 + 认证 schemas 字段/约束（纯单元，无 DB/Redis）。

覆盖轴1：bcrypt 校验行为；AuthRegister/AuthLogin/UserOut 请求/响应契约。
"""
import pytest

from backend.api.schemas import AuthLogin, AuthRegister, UserOut
from backend.auth.password import hash_password, verify_password


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
