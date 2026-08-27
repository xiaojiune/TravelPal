"""认证 API：注册 / 登录 / 登出 / me（httpOnly Cookie + Redis Session）。"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import AuthLogin, AuthRegister, UserOut
from backend.auth import create_session, get_session, hash_password, revoke_session, verify_password
from backend.config import settings
from backend.data.model.database import get_session as get_db_session
from backend.data.model.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])

_SESSION_COOKIE = "session_id"


def _to_user_out(user: User) -> UserOut:
    """User ORM → UserOut。"""
    return UserOut(
        id=str(user.id), email=user.email, nickname=user.nickname, role=user.role, is_active=user.is_active
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


async def get_current_user(request: Request, session: AsyncSession = Depends(get_db_session)) -> User:
    """FastAPI 依赖：从 httpOnly cookie 解析会话，返回当前登录用户（未登录 401）。"""
    sid = request.cookies.get(_SESSION_COOKIE)
    user_id = get_session(sid)  # Redis 会话（同步）
    user = await _load_user(session, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    return user


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserOut)
async def register(req: AuthRegister, response: Response, session: AsyncSession = Depends(get_db_session)):
    """注册并自动登录（写会话 Cookie）。"""
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
    """登录：校验密码，创建会话并写 Cookie。"""
    email = req.email.strip().lower()
    user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None or not user.is_active or not user.password_hash or not verify_password(
        req.password, user.password_hash
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱或密码错误")
    sid = create_session(str(user.id))
    if sid is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="会话创建失败")
    _set_session_cookie(response, sid)
    return _to_user_out(user)


@router.post("/logout")
async def logout(request: Request, response: Response):
    """登出：撤销会话并清除 Cookie。"""
    sid = request.cookies.get(_SESSION_COOKIE)
    if sid:
        revoke_session(sid)
    response.delete_cookie(_SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/me", response_model=UserOut)
async def me(current: User = Depends(get_current_user)):
    """返回当前登录用户信息。"""
    return _to_user_out(current)
