"""FastAPI 路由定义：POI 查询、行程规划、Agent 对话、方案分享、异步任务。"""

import json
import traceback
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.chat import build_chat_messages, stream_orchestrator
from backend.agent.tools import parse_biz_hours
from backend.api.auth import get_current_user_optional
from backend.api.schemas import (
    ChatHistoryResponse,
    ChatRequest,
    FeedbackCreate,
    PlanRequest,
    POILookupItem,
    POILookupRequest,
    POILookupResponse,
    ShareCreate,
    ShareDeleteRequest,
    ShareDetail,
    ShareListResponse,
    ShareSummary,
    TaskCancelResponse,
    TaskDetail,
    TaskListItem,
    TaskListResponse,
    TaskSubmitResponse,
)
from backend.infrastructure.external.amap.amap_loader import get_poi_details
from backend.infrastructure.db.checkpointer import get_checkpointer
from backend.infrastructure.data.conversations import (
    get_history_messages,
    get_or_create_conversation,
    get_recent_conversation,
)
from backend.infrastructure.db.database import get_session
from backend.infrastructure.db.models import FeedbackRecord, PlanTask, SharedPlan, User
from backend.tasks.submit import submit_task

router = APIRouter()

# 对话链路不暴露的方案修改工具（add_poi/remove_poi）：
# 异步路径返回 task_id 后前端无轮询回传（结果会丢），故对话内禁用；
# 工具本身保留（单一事实来源，MCP 等外部调用方仍可用）。见 ADR-009 场景二。
_CHAT_EXCLUDE_TOOLS = {"add_poi", "remove_poi"}

# ================== 路由端点 ==================


@router.post("/api/poi-lookup", response_model=POILookupResponse)
async def poi_lookup(req: POILookupRequest):
    """批量查询 POI 坐标和地址。

    前端传入城市 + 名称列表，后端调用高德 POI 搜索 API，
    返回每个名称的坐标和地址。未找到的名称列入 failed 列表，
    若跨城市则附带建议地址。

    Args:
        req: POI 查询请求，含城市名和名称列表。

    Returns:
        POILookupResponse: 查询结果，items 为成功项，failed 为失败列表。
    """
    items: list[POILookupItem] = []
    failed: list[str] = []

    for name in req.names:
        try:
            result = get_poi_details(name, req.city)
            if isinstance(result, str):
                failed.append(result)
            else:
                lon, lat, biz_hours, address, pname, cityname, actual_name, _ = result
                parsed = await parse_biz_hours(biz_hours) if biz_hours else None
                tw_start = parsed[0] if parsed else None
                tw_end = parsed[1] if parsed else None
                items.append(
                    POILookupItem(
                        name=actual_name,
                        lon=lon,
                        lat=lat,
                        address=address,
                        tw_start=tw_start,
                        tw_end=tw_end,
                    )
                )
        except Exception:
            traceback.print_exc()
            failed.append(f"未在{req.city}找到{name}，请尝试更换搜索词")

    return POILookupResponse(items=items, failed=failed)


# ---------- 规划相关 ----------


@router.post("/api/or-ca", response_model=TaskSubmitResponse)
async def or_ca(
    req: PlanRequest,
    current: User | None = Depends(get_current_user_optional),
):
    """提交 OR-CA 方案建议任务（异步执行）。

    建议模式（CA）需拉取完整驾车路径 API 构建成本矩阵，耗时可达数十秒；
    改为提交异步任务，立即返回 task_id，前端轮询 GET /api/tasks/{id} 获取结果。
    实际求解在 Celery worker 中执行（复用 suggest 阶段缓存的矩阵则更快）。

    Args:
        req: 规划请求，n_days 不指定，mode 固定走建议模式。
        current: 当前登录用户（可选）；登录时任务归属该 user_id，匿名则为 None。

    Returns:
        TaskSubmitResponse: { task_id: str }，前端据此轮询。

    Raises:
        HTTPException 500: 任务创建失败。
    """
    try:
        task_id = await submit_task("or-ca", req.model_dump(), user_id=current.id if current else None)  # pyright: ignore[reportArgumentType]
        return TaskSubmitResponse(task_id=task_id)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/or-vns", response_model=TaskSubmitResponse)
async def or_vns(
    req: PlanRequest,
    current: User | None = Depends(get_current_user_optional),
):
    """提交 OR-VNS 完整规划任务（异步执行）。

    n_days 为必填，mode 可选 "fast"(CA) 或 "deep"(VNS)。
    若 req 携带 cost_matrix/dist_matrix（来自 suggest 响应），
    则复用矩阵跳过驾车 API 调用，执行较快。
    任务在 Celery worker 中执行，返回 task_id 供前端轮询。

    Args:
        req: 规划请求，含 n_days 与求解模式。
        current: 当前登录用户（可选）；登录时任务归属该 user_id，匿名则为 None。

    Returns:
        TaskSubmitResponse: { task_id: str }，前端据此轮询。

    Raises:
        HTTPException 400: n_days 未指定时。
        HTTPException 500: 任务创建失败。
    """
    if req.n_days is None:
        raise HTTPException(status_code=400, detail="n_days is required for planning")
    try:
        task_id = await submit_task("or-vns", req.model_dump(), user_id=current.id if current else None)  # pyright: ignore[reportArgumentType]
        return TaskSubmitResponse(task_id=task_id)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Agent 对话 ----------


@router.get("/api/chat/history", response_model=ChatHistoryResponse)
async def chat_history(
    session: AsyncSession = Depends(get_session),
    current: User | None = Depends(get_current_user_optional),
):
    """取登录用户最近未过期会话的历史（不含 system），供打开 Agent 面板恢复上下文。

    只读通道：**不创建会话**（避免只读访问落库）。返回最近会话 id 与该会话的
    checkpoint 历史消息；游客或用户无历史时返回 { conversation_id: None, messages: [] }，
    前端据此走新建会话路径。

    Args:
        session: 数据库会话（会话记录只读查询）。
        current: 当前登录用户（可选）；仅登录用户可恢复历史，游客返回空。

    Returns:
        ChatHistoryResponse: { conversation_id, messages }。
    """
    conv = await get_recent_conversation(session, current.id if current else None)  # pyright: ignore[reportArgumentType]
    if conv is None:
        return ChatHistoryResponse()
    history = await get_history_messages(str(conv.id))
    messages = [m for m in history if m.get("role") != "system"]
    return ChatHistoryResponse(conversation_id=str(conv.id), messages=messages)


@router.post("/api/chat")
async def chat(
    req: ChatRequest,
    session: AsyncSession = Depends(get_session),
    current: User | None = Depends(get_current_user_optional),
):
    """LLM Agent 对话接口，SSE 流式输出（含会话记忆）。

    编排由 LangGraph 单 Agent（orchestrator.py）驱动：LLM 决策 → 工具分发
    （TOOL_REGISTRY，含 poi_lookup 等）→ SSE 事件流（content/tool_status/tool_result）。
    会话（conversation）懒创建：首条消息不带 conversation_id 时新建，SSE 首事件返回
    会话 id 供前端存下续接；后续携带 conversation_id 时读取历史续接（跨轮次记忆）。

    Args:
        req: 聊天请求，含 message 和可选的 plan_result / form_context / conversation_id。
        session: 数据库会话（会话记录存取）。
        current: 当前登录用户（可选）；登录时会话归属该 user_id。

    Returns:
        StreamingResponse: SSE 流式响应，逐 token 推送内容（首事件为 conversation id）。

    Raises:
        HTTPException 500: LLM 调用异常或数据格式错误。
    """
    try:
        conv, created = await get_or_create_conversation(
            session, req.conversation_id, current.id if current else None  # pyright: ignore[reportArgumentType]
        )
        if created:
            # 新建会话（首条/过期重建）：build_chat_messages（system + 当前消息）
            messages = build_chat_messages(req.message, req.plan_result, req.form_context)
        else:
            history = await get_history_messages(str(conv.id))
            messages = (
                list(history) + [{"role": "user", "content": req.message}]
                if history
                else build_chat_messages(req.message, req.plan_result, req.form_context)
            )
        thread_id = str(conv.id)
        checkpointer = get_checkpointer()

        async def _stream():
            """SSE 生成器：先发会话 id，再映射 LangGraph 编排事件流。"""
            # 懒建/复用的会话 id 通知前端（前端存下后后续轮携带续接）
            yield f"data: {json.dumps({'type': 'conversation', 'conversation_id': thread_id})}\n\n"
            try:
                async for event_type, data in stream_orchestrator(
                    messages,
                    exclude=_CHAT_EXCLUDE_TOOLS,
                    plan_result=req.plan_result,
                    form_context=req.form_context,
                    checkpointer=checkpointer,
                    thread_id=thread_id,
                ):
                    if event_type == "content":
                        yield f"data: {json.dumps({'type': 'content', 'data': data})}\n\n"
                    elif event_type == "tool_status":
                        yield f"data: {json.dumps({'type': 'tool_status', 'data': f'正在执行 {data}...'})}\n\n"
                    elif event_type == "tool_result":
                        yield f"data: {json.dumps({'type': 'tool_result', 'data': data})}\n\n"
            except Exception:
                yield f"data: {json.dumps({'type': 'error', 'data': '对话生成失败，请重试'})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        return StreamingResponse(
            _stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ================== 方案分享 ==================


@router.get("/api/shares", response_model=ShareListResponse)
async def list_shares(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """获取方案分享分页列表。

    仅返回摘要字段（id/city/n_days/cost/spot_count/note/created_at），
    不加载 JSONB 大字段（plan_result），避免列表页传输大量数据。

    Args:
        page: 页码，从 1 开始。
        page_size: 每页条数，最大 100。

    Returns:
        ShareListResponse: { items, total, page, page_size }。
    """
    count_q = select(func.count(SharedPlan.id))
    total = (await session.execute(count_q)).scalar() or 0

    q = select(SharedPlan).order_by(SharedPlan.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(q)).scalars().all()

    items = [
        ShareSummary(
            id=str(r.id),
            city=r.city,  # type: ignore[arg-type]
            hotel=r.hotel,  # type: ignore[arg-type]
            n_days=r.n_days,  # type: ignore[arg-type]
            cost=r.cost,  # type: ignore[arg-type]
            spot_count=r.spot_count,  # type: ignore[arg-type]
            note=r.note,  # type: ignore[arg-type]
            created_at=r.created_at.isoformat() if r.created_at is not None else "",
        )
        for r in rows
    ]
    return ShareListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/api/shares/{record_id}", response_model=ShareDetail)
async def get_share_detail(record_id: UUID, session: AsyncSession = Depends(get_session)):
    """获取单条方案分享的完整数据（含 plan_result 全量 JSONB）。

    Args:
        record_id: 记录 UUID。

    Returns:
        ShareDetail: 含 plan_result/request_params 等完整字段。

    Raises:
        HTTPException 404: 记录不存在。
    """
    r = await session.get(SharedPlan, record_id)
    if not r:
        raise HTTPException(status_code=404, detail="记录不存在")
    return ShareDetail(
        id=str(r.id),
        city=r.city,  # type: ignore[arg-type]
        hotel=r.hotel,  # type: ignore[arg-type]
        n_days=r.n_days,  # type: ignore[arg-type]
        cost=r.cost,  # type: ignore[arg-type]
        spot_count=r.spot_count,  # type: ignore[arg-type]
        note=r.note,  # type: ignore[arg-type]
        plan_result=r.plan_result,  # type: ignore[arg-type]
        request_params=r.request_params,  # type: ignore[arg-type]
        created_at=r.created_at.isoformat() if r.created_at is not None else "",
    )


@router.post("/api/shares", status_code=201)
async def create_share(
    req: ShareCreate,
    session: AsyncSession = Depends(get_session),
    current: User | None = Depends(get_current_user_optional),
):
    """保存一条方案分享（到分享站）。

    设计说明：登录用户归属 user_id；未登录访客仍零门槛可用（user_id 为 None），
    device_id 由前端 localStorage 生成，仅用于匿名删除鉴权。

    Args:
        req: ShareCreate，包含 city/n_days/plan_result 等必填字段。
        session: 数据库会话（依赖注入）。
        current: 当前登录用户（可选）；登录时写 user_id，匿名则为 None。

    Returns:
        dict: { id: str } 新创建的记录 UUID。

    Raises:
        HTTPException 422: 请求体校验失败（Pydantic 自动处理）。
    """
    record = SharedPlan(
        user_id=current.id if current else None,
        device_id=req.device_id,
        note=req.note,
        city=req.city,
        hotel=req.hotel,
        n_days=req.n_days,
        cost=req.cost,
        spot_count=req.spot_count,
        plan_result=req.plan_result,
        request_params=req.request_params,
    )
    session.add(record)
    await session.commit()
    return {"id": str(record.id)}


@router.post("/api/feedback", status_code=201)
async def create_feedback(
    req: FeedbackCreate,
    session: AsyncSession = Depends(get_session),
    current: User | None = Depends(get_current_user_optional),
):
    """保存一条用户反馈（/about 页面问卷）。

    Args:
        req: FeedbackCreate，content 必填，name/contact/rating/page 可选。
        session: 数据库会话（依赖注入）。
        current: 当前登录用户（可选）；登录时归属该 user_id，匿名则为 None。

    Returns:
        dict: { id: str } 新创建的反馈 UUID。

    Raises:
        HTTPException 422: 请求体校验失败（Pydantic 自动处理）。
    """
    record = FeedbackRecord(
        user_id=current.id if current else None,
        name=req.name,
        contact=req.contact,
        content=req.content,
        rating=req.rating,
        page=req.page,
    )
    session.add(record)
    await session.commit()
    return {"id": str(record.id)}


@router.delete("/api/shares/{record_id}")
async def delete_share(
    record_id: UUID,
    req: ShareDeleteRequest,
    session: AsyncSession = Depends(get_session),
    current: User | None = Depends(get_current_user_optional),
):
    """删除一条方案分享（登录按 user_id，匿名按 device_id）。

    设计说明：登录用户只能删除归属自己（user_id 匹配）的记录，无法删除匿名记录；
    未登录访客按 device_id 校验（软鉴权），与创建时一致。

    Args:
        record_id: 记录 UUID。
        req: ShareDeleteRequest，包含 device_id。
        session: 数据库会话（依赖注入）。
        current: 当前登录用户（可选）。

    Returns:
        dict: { ok: true }

    Raises:
        HTTPException 404: 记录不存在。
        HTTPException 403: 无权删除（user_id 或 device_id 不匹配）。
    """
    r = await session.get(SharedPlan, record_id)
    if not r:
        raise HTTPException(status_code=404, detail="记录不存在")
    if current is not None:
        if r.user_id != current.id:  # pyright: ignore[reportGeneralTypeIssues]
            raise HTTPException(status_code=403, detail="无权删除此记录")
    else:
        if r.device_id is not None and r.device_id != req.device_id:  # pyright: ignore[reportGeneralTypeIssues]
            raise HTTPException(status_code=403, detail="无权删除此记录")
    await session.delete(r)
    await session.commit()
    return {"ok": True}


# ================== 异步规划任务 ==================


@router.get("/api/tasks/{task_id}", response_model=TaskDetail)
async def get_task_detail(task_id: UUID, session: AsyncSession = Depends(get_session)):
    """获取异步规划任务的状态详情，供前端轮询。

    status 四态：pending（排队中）/ running（执行中）/ done（成功）/ failed（失败）。
    result 仅 done 时存在（suggest 完整响应或完整 PlanResult），
    error 仅 failed 时存在。

    Args:
        task_id: 任务 UUID（由 POST /api/suggest 或 /api/plan 返回）。

    Returns:
        TaskDetail: { task_id, task_type, status, result?, error? }。

    Raises:
        HTTPException 404: 任务不存在。
    """
    task = await session.get(PlanTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return TaskDetail(
        task_id=str(task.id),
        task_type=task.task_type,  # type: ignore[arg-type]
        status=task.status,  # type: ignore[arg-type]
        result=task.result,  # type: ignore[arg-type]
        error=task.error,  # type: ignore[arg-type]
    )


@router.get("/api/tasks", response_model=TaskListResponse)
async def list_tasks(
    session: AsyncSession = Depends(get_session),
    current: User | None = Depends(get_current_user_optional),
    limit: int = Query(20, ge=1, le=100),
):
    """列出当前登录用户最近的任务（供任务面板展示）。

    归属：登录用户按 user_id 过滤；匿名用户无任务归属键，返回空列表。

    Args:
        session: DB 会话。
        current: 当前登录用户（可选），匿名返回空。
        limit: 返回条数上限，默认 20。

    Returns:
        TaskListResponse: { tasks: [...] }。
    """
    if current is None:
        return TaskListResponse(tasks=[])
    rows = (
        (
            await session.execute(
                select(PlanTask)
                .where(PlanTask.user_id == current.id)
                .order_by(PlanTask.created_at.desc())
                .limit(limit)
            )
        ).scalars()
    ).all()
    return TaskListResponse(
        tasks=[
            TaskListItem(
                task_id=str(t.id),
                task_type=t.task_type,  # type: ignore[arg-type]
                status=t.status,  # type: ignore[arg-type]
                created_at=t.created_at.isoformat() if t.created_at is not None else "",
                finished_at=t.finished_at.isoformat() if t.finished_at is not None else None,
            )
            for t in rows
        ]
    )


@router.post("/api/tasks/{task_id}/cancel", response_model=TaskCancelResponse)
async def cancel_task(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),
    current: User | None = Depends(get_current_user_optional),
):
    """请求取消一个异步规划任务（pending/running → canceled）。

    协作式取消：端点只把 status 置为 canceled，worker 在执行前/执行中探测到后
    协作退出（秒级中断）；finished_at 由 worker 收尾，避免与进行中的任务竞态覆盖。

    Args:
        task_id: 任务 UUID。
        current: 当前登录用户（可选，用于归属校验）。

    Returns:
        TaskCancelResponse: { ok, status }。

    Raises:
        HTTPException 404: 任务不存在。
        HTTPException 403: 归属校验失败（登录用户仅可取消自己的任务）。
        HTTPException 409: 任务已终态（done/failed），无法取消。
    """
    task = await session.get(PlanTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if current is not None and task.user_id is not None and task.user_id != current.id:  # pyright: ignore[reportGeneralTypeIssues]
        raise HTTPException(status_code=403, detail="无权取消此任务")
    cur_status: str = task.status  # type: ignore[assignment]
    if cur_status == "done" or cur_status == "failed":
        raise HTTPException(status_code=409, detail="任务已结束，无法取消")
    if cur_status != "canceled":
        task.status = "canceled"  # type: ignore[assignment]
        await session.commit()
    return TaskCancelResponse(ok=True, status=cur_status)


@router.delete("/api/tasks/{task_id}")
async def delete_task(task_id: UUID, session: AsyncSession = Depends(get_session)):
    """删除一条异步规划任务记录（用户主动清理）。

    任务历史默认保留，暂不做软删除/定期归档；
    删除由用户主动发起，用于清理不再需要的任务。

    Args:
        task_id: 任务 UUID。

    Returns:
        dict: { ok: bool }。

    Raises:
        HTTPException 404: 任务不存在。
    """
    task = await session.get(PlanTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    await session.delete(task)
    await session.commit()
    return {"ok": True}
