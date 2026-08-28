"""认证 API：注册 / 登录 / 登出 / me（httpOnly Cookie + Redis Session）。"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import AuthLogin, AuthRegister, UserOut
from backend.auth import (
    create_session,
    get_session,
    hash_password,
    revoke_session,
    verify_password,
)
from backend.config import settings
from backend.data.model.database import get_session as get_db_session
from backend.data.model.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])

_SESSION_COOKIE = "session_id"


def _to_user_out(user: User) -> UserOut:
    """User ORM → UserOut。"""
    return UserOut(
        id=str(user.id),
        email=user.email,  # pyright: ignore[reportArgumentType]
        nickname=user.nickname,  # pyright: ignore[reportArgumentType]
        role=user.role,  # pyright: ignore[reportArgumentType]
        is_active=user.is_active,  # pyright: ignore[reportArgumentType]
    )


def _set_session_cookie(response: Response, session_id: str) -> None:
    """写 httpOnly + SameSite=Lax 的会话 Cookie。"""
    response.set_cookie(
        key=_SESSION_COOKIE,
        value=session_id,
        max_age=settings.SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=False,  # 生产（HTTPS）应置 True
        path="/",
    )


async def _load_user(session: AsyncSession, user_id: str | None) -> User | None:
    """按 user_id 字符串加载 User；无效或不存在返回 None。"""
    if not user_id:
        return None
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        return None
    return await session.get(User, uid)


async def _resolve_user_from_request(request: Request, session: AsyncSession) -> User | None:
    """从请求会话 Cookie 解析当前用户；未登录/停用/会话失效返回 None。

    Args:
        request: 当前请求（读取会话 Cookie）。
        session: 数据库会话。

    Returns:
        User | None: 当前登录用户；未登录、会话失效或用户已停用返回 None。
    """
    sid = request.cookies.get(_SESSION_COOKIE)
    user_id = get_session(sid)  # Redis 会话（同步）
    user = await _load_user(session, user_id)
    if user is None or not user.is_active:  # pyright: ignore[reportGeneralTypeIssues]
        return None
    return user


async def get_current_user(request: Request, session: AsyncSession = Depends(get_db_session)) -> User:
    """FastAPI 依赖：从 httpOnly cookie 解析会话，返回当前登录用户。

    Args:
        request: 当前请求（读取会话 Cookie）。
        session: 数据库会话。

    Returns:
        User: 当前登录用户。

    Raises:
        HTTPException 401: 未登录、会话失效或用户已停用。
    """
    user = await _resolve_user_from_request(request, session)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    return user


async def get_current_user_optional(request: Request, session: AsyncSession = Depends(get_db_session)) -> User | None:
    """FastAPI 依赖：可选鉴权——从 httpOnly cookie 解析会话，未登录返回 None 而非抛 401。

    供「登录则归属、未登录则匿名」的端点使用（/api/shares、/api/feedback、/api/suggest、/api/plan），
    不强锁全站，保障访客零门槛可用（user-system.md 轴3）。

    Args:
        request: 当前请求（读取会话 Cookie）。
        session: 数据库会话。

    Returns:
        User | None: 当前登录用户；未登录、会话失效或用户已停用返回 None。
    """
    return await _resolve_user_from_request(request, session)


async def require_admin(current: User = Depends(get_current_user)) -> User:
    """FastAPI 依赖：要求当前用户具备管理员权限，否则拒绝（RBAC）。

    放行 role 为 admin 或 super_admin 的登录用户：后端管理 API 对两者均就绪
    （普通 admin 可经脚本/HTTP 调用，前端界面暂仅 super_admin 激活——见 user-system.md 轴5）。
    普通 user（含 guest）返回 403。

    Args:
        current: 当前登录用户（依赖注入）。

    Returns:
        User: 当前用户（已确认具备管理员权限）。

    Raises:
        HTTPException 403: 当前用户非 admin/super_admin 角色。
    """
    if current.role not in ("admin", "super_admin"):  # pyright: ignore[reportGeneralTypeIssues]
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return current


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserOut)
async def register(req: AuthRegister, response: Response, session: AsyncSession = Depends(get_db_session)):
    """注册用户并自动登录。

    Args:
        req: 注册请求（邮箱/密码/昵称）。
        response: 响应对象，登录后写入会话 Cookie。
        session: 数据库会话。

    Returns:
        UserOut: 新注册用户信息。

    Raises:
        HTTPException 409: 邮箱已注册。
    """
    email = req.email.strip().lower()
    existing = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该邮箱已注册")
    user = User(
        email=email,
        password_hash=hash_password(req.password),
        nickname=req.nickname,
        role="user",
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    sid = create_session(str(user.id))
    if sid:
        _set_session_cookie(response, sid)
    return _to_user_out(user)


@router.post("/login", response_model=UserOut)
async def login(req: AuthLogin, response: Response, session: AsyncSession = Depends(get_db_session)):
    """登录：校验密码并创建会话。

    Args:
        req: 登录请求（邮箱/密码）。
        response: 响应对象，成功后写入会话 Cookie。
        session: 数据库会话。

    Returns:
        UserOut: 当前用户信息。

    Raises:
        HTTPException 401: 邮箱或密码错误。
        HTTPException 503: 会话创建失败（会话不可用）。
    """
    email = req.email.strip().lower()
    user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if (
        user is None
        or not user.is_active  # pyright: ignore[reportGeneralTypeIssues]
        or not user.password_hash  # pyright: ignore[reportGeneralTypeIssues]
        or not verify_password(req.password, user.password_hash)  # pyright: ignore[reportArgumentType]
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱或密码错误")
    sid = create_session(str(user.id))
    if sid is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="会话创建失败")
    _set_session_cookie(response, sid)
    return _to_user_out(user)


@router.post("/logout")
async def logout(request: Request, response: Response):
    """登出：撤销会话并清除 Cookie。

    Args:
        request: 当前请求（读取会话 Cookie）。
        response: 响应对象，用于清除 Cookie。

    Returns:
        dict: {"ok": True}。
    """
    sid = request.cookies.get(_SESSION_COOKIE)
    if sid:
        revoke_session(sid)
    response.delete_cookie(_SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/me", response_model=UserOut)
async def me(current: User = Depends(get_current_user)):
    """返回当前登录用户信息。

    Args:
        current: 当前登录用户（依赖注入）。

    Returns:
        UserOut: 当前用户信息。
    """
    return _to_user_out(current)
