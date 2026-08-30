"""管理员操作台 API：用户 / 任务 / 反馈的只读分页列表（require_admin 保护）。

轴5（user-system.md）：后端管理 API 对 admin 与 super_admin 均放行（require_admin），
普通 admin 可经脚本/HTTP 调用；前端界面暂仅 super_admin 激活。全部只读，不做删除/禁用。
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import require_admin
from backend.api.schemas import (
    AdminFeedback,
    AdminFeedbackResponse,
    AdminTask,
    AdminTasksResponse,
    AdminUser,
    AdminUsersResponse,
)
from backend.data.model.database import get_session
from backend.data.model.models import FeedbackRecord, PlanTask, User

router = APIRouter(prefix="/api/admin", tags=["admin"])

# 分页上限（与分享站一致，防单页过大）
_MAX_PAGE_SIZE = 100


@router.get("/users", response_model=AdminUsersResponse)
async def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=_MAX_PAGE_SIZE),
    session: AsyncSession = Depends(get_session),
    current: User = Depends(require_admin),
):
    """分页列出全部用户（含 guest/user/admin/super_admin）。

    Args:
        page: 页码，从 1 开始。
        page_size: 每页条数，最大 100。
        session: 数据库会话。
        current: 当前用户（require_admin 校验）。

    Returns:
        AdminUsersResponse: { items, total, page, page_size }。

    Raises:
        HTTPException 403: 当前用户非 admin/super_admin（require_admin）。
    """
    total = (await session.execute(select(func.count(User.id)))).scalar() or 0
    q = select(User).order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(q)).scalars().all()
    items = [
        AdminUser(
            id=str(r.id),
            email=r.email,  # type: ignore[arg-type]
            nickname=r.nickname,  # type: ignore[arg-type]
            role=r.role,  # type: ignore[arg-type]
            is_active=r.is_active,  # type: ignore[arg-type]
            created_at=r.created_at.isoformat() if r.created_at is not None else "",
        )
        for r in rows
    ]
    return AdminUsersResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/tasks", response_model=AdminTasksResponse)
async def list_tasks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=_MAX_PAGE_SIZE),
    session: AsyncSession = Depends(get_session),
    current: User = Depends(require_admin),
):
    """分页列出全部异步规划任务（or-ca/or-vns）。

    Args:
        page: 页码。
        page_size: 每页条数。
        session: 数据库会话。
        current: 当前用户（require_admin 校验）。

    Returns:
        AdminTasksResponse: { items, total, page, page_size }。

    Raises:
        HTTPException 403: 当前用户非 admin/super_admin（require_admin）。
    """
    total = (await session.execute(select(func.count(PlanTask.id)))).scalar() or 0
    q = select(PlanTask).order_by(PlanTask.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(q)).scalars().all()
    items = [
        AdminTask(
            id=str(r.id),
            task_type=r.task_type,  # type: ignore[arg-type]
            status=r.status,  # type: ignore[arg-type]
            created_at=r.created_at.isoformat() if r.created_at is not None else "",
            finished_at=r.finished_at.isoformat() if r.finished_at is not None else None,
        )
        for r in rows
    ]
    return AdminTasksResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/feedback", response_model=AdminFeedbackResponse)
async def list_feedback(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=_MAX_PAGE_SIZE),
    session: AsyncSession = Depends(get_session),
    current: User = Depends(require_admin),
):
    """分页列出全部用户反馈。

    Args:
        page: 页码。
        page_size: 每页条数。
        session: 数据库会话。
        current: 当前用户（require_admin 校验）。

    Returns:
        AdminFeedbackResponse: { items, total, page, page_size }。

    Raises:
        HTTPException 403: 当前用户非 admin/super_admin（require_admin）。
    """
    total = (await session.execute(select(func.count(FeedbackRecord.id)))).scalar() or 0
    q = (
        select(FeedbackRecord)
        .order_by(FeedbackRecord.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await session.execute(q)).scalars().all()
    items = [
        AdminFeedback(
            id=str(r.id),
            name=r.name,  # type: ignore[arg-type]
            contact=r.contact,  # type: ignore[arg-type]
            content=r.content,  # type: ignore[arg-type]
            rating=r.rating,  # type: ignore[arg-type]
            page=r.page,  # type: ignore[arg-type]
            created_at=r.created_at.isoformat() if r.created_at is not None else "",
        )
        for r in rows
    ]
    return AdminFeedbackResponse(items=items, total=total, page=page, page_size=page_size)
