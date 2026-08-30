"""认证领域逻辑：密码哈希（bcrypt）。属 domain 核心，纯逻辑、无外部 I/O。"""
import bcrypt


def hash_password(plain: str) -> str:
    """对明文密码做 bcrypt 哈希（自动加盐）。

    Args:
        plain: 用户原始密码。

    Returns:
        str: bcrypt 哈希串（含盐，可直接入库）。
    """
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """校验明文密码与哈希是否匹配。

    Args:
        plain: 待校验明文密码。
        hashed: 存储的 bcrypt 哈希。

    Returns:
        bool: 匹配返回 True；哈希格式异常返回 False（不抛异常）。
    """
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False
