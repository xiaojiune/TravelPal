"""FastAPI 路由定义：POI 查询、行程规划、Agent 对话、历史记录、异步任务。"""

import json
import traceback
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.chat import build_chat_messages, stream_orchestrator
from backend.agent.tools import parse_biz_hours
from backend.api.schemas import (
    ChatRequest,
    HistoryCreate,
    HistoryDeleteRequest,
    HistoryDetail,
    HistoryListResponse,
    HistorySummary,
    PlanRequest,
    POILookupItem,
    POILookupRequest,
    POILookupResponse,
    TaskDetail,
    TaskSubmitResponse,
)
from backend.data.amap_loader import get_poi_details
from backend.data.model.database import get_session
from backend.data.model.models import HistoryRecord, PlanTask
from backend.tasks.submit import submit_task

router = APIRouter()

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


@router.post("/api/suggest", response_model=TaskSubmitResponse)
async def suggest(req: PlanRequest):
    """提交方案建议任务（异步执行）。

    建议模式（CA）需拉取完整驾车路径 API 构建成本矩阵，耗时可达数十秒；
    改为提交异步任务，立即返回 task_id，前端轮询 GET /api/tasks/{id} 获取结果。
    实际求解在 Celery worker 中执行（复用 suggest 阶段缓存的矩阵则更快）。

    Args:
        req: 规划请求，n_days 不指定，mode 固定走建议模式。

    Returns:
        TaskSubmitResponse: { task_id: str }，前端据此轮询。

    Raises:
        HTTPException 500: 任务创建失败。
    """
    try:
        task_id = await submit_task("suggest", req.model_dump())
        return TaskSubmitResponse(task_id=task_id)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/plan", response_model=TaskSubmitResponse)
async def plan(req: PlanRequest):
    """提交完整规划任务（异步执行）。

    n_days 为必填，mode 可选 "fast"(CA) 或 "deep"(VNS)。
    若 req 携带 cost_matrix/dist_matrix（来自 suggest 响应），
    则复用矩阵跳过驾车 API 调用，执行较快。
    任务在 Celery worker 中执行，返回 task_id 供前端轮询。

    Args:
        req: 规划请求，含 n_days 与求解模式。

    Returns:
        TaskSubmitResponse: { task_id: str }，前端据此轮询。

    Raises:
        HTTPException 400: n_days 未指定时。
        HTTPException 500: 任务创建失败。
    """
    if req.n_days is None:
        raise HTTPException(status_code=400, detail="n_days is required for planning")
    try:
        task_id = await submit_task("plan", req.model_dump())
        return TaskSubmitResponse(task_id=task_id)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Agent 对话 ----------


@router.post("/api/chat")
async def chat(req: ChatRequest):
    """LLM Agent 对话接口，SSE 流式输出。

    编排由 LangGraph 单 Agent（orchestrator.py）驱动：LLM 决策 → 工具分发
    （TOOL_REGISTRY，含 poi_lookup 等）→ SSE 事件流（content/tool_status/tool_result）。

    Args:
        req: 聊天请求，含 message 和可选的 plan_result / form_context 上下文。

    Returns:
        StreamingResponse: SSE 流式响应，逐 token 推送内容。

    Raises:
        HTTPException 500: LLM 调用异常或数据格式错误。
    """
    try:
        messages = build_chat_messages(req.message, req.plan_result, req.form_context)

        async def _stream():
            """SSE 生成器：LangGraph 编排产出事件，映射为 SSE 事件流。"""
            try:
                async for event_type, data in stream_orchestrator(
                    messages,
                    plan_result=req.plan_result,
                    form_context=req.form_context,
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


# ================== 历史记录（分享站） ==================


@router.get("/api/history", response_model=HistoryListResponse)
async def list_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """获取历史记录分页列表。

    仅返回摘要字段（id/city/n_days/cost/spot_count/note/created_at），
    不加载 JSONB 大字段（plan_result），避免列表页传输大量数据。

    Args:
        page: 页码，从 1 开始。
        page_size: 每页条数，最大 100。

    Returns:
        HistoryListResponse: { items, total, page, page_size }。
    """
    count_q = select(func.count(HistoryRecord.id))
    total = (await session.execute(count_q)).scalar() or 0

    q = select(HistoryRecord).order_by(HistoryRecord.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(q)).scalars().all()

    items = [
        HistorySummary(
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
    return HistoryListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/api/history/{record_id}", response_model=HistoryDetail)
async def get_history_detail(record_id: UUID, session: AsyncSession = Depends(get_session)):
    """获取单条历史记录的完整数据（含 plan_result 全量 JSONB）。

    Args:
        record_id: 记录 UUID。

    Returns:
        HistoryDetail: 含 plan_result/request_params 等完整字段。

    Raises:
        HTTPException 404: 记录不存在。
    """
    r = await session.get(HistoryRecord, record_id)
    if not r:
        raise HTTPException(status_code=404, detail="记录不存在")
    return HistoryDetail(
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


@router.post("/api/history", status_code=201)
async def create_history(req: HistoryCreate, session: AsyncSession = Depends(get_session)):
    """保存一条历史记录（分享方案到分享站）。

    设计说明：device_id 由前端 localStorage 自动生成，服务端不做强鉴权——
    这是软鉴权设计。核心考量：
    1. 不引入注册/登录系统，保持访客零门槛
    2. device_id 仅用于删除时校验「是否是本人」，防止误删他人方案
    3. device_id 无法防恶意攻击（前端可伪造），但此场景无敏感数据，可接受

    Args:
        req: HistoryCreate，包含 city/n_days/plan_result 等必填字段。

    Returns:
        dict: { id: str } 新创建的记录 UUID。

    Raises:
        HTTPException 422: 请求体校验失败（Pydantic 自动处理）。
    """
    record = HistoryRecord(
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


@router.delete("/api/history/{record_id}")
async def delete_history(
    record_id: UUID,
    req: HistoryDeleteRequest,
    session: AsyncSession = Depends(get_session),
):
    """删除一条历史记录（需 device_id 匹配创建者）。

    Args:
        record_id: 记录 UUID。
        req: HistoryDeleteRequest，包含 device_id。

    Returns:
        dict: { ok: true }

    Raises:
        HTTPException 404: 记录不存在。
        HTTPException 403: device_id 不匹配，无权删除。
    """
    r = await session.get(HistoryRecord, record_id)
    if not r:
        raise HTTPException(status_code=404, detail="记录不存在")
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
