"""FastAPI 路由定义：POI 查询、行程规划、Agent 对话、历史记录。"""

import json
import traceback
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.chat import build_chat_messages, chat_stream
from backend.agent.tools import TOOL_REGISTRY, parse_biz_hours
from backend.agent.tools.prompts import TOOL_DEFINITIONS
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
)
from backend.config import AMAP_JS_KEY, AMAP_JS_SECURITY_CODE
from backend.data.amap_loader import get_poi_details
from backend.data.model.database import get_session
from backend.data.model.models import HistoryRecord
from backend.engine.pipeline import run_planning

router = APIRouter()

# ================== 辅助函数 ==================

def _build_poi_cache(req: PlanRequest):
    """将 PlanRequest 转换为 run_planning 所需的 poi_cache 格式。

    前端传来的坐标数据可直接映射，无需额外转换。
    时间窗以 (start, end) 元组形式传递。

    Args:
        req: 前端传入的规划请求，含酒店/景点坐标及时间窗。

    Returns:
        dict: {"hotel": {...酒店信息...}, "spots": [...景点列表...]}。
    """
    hotel = {
        "name": req.hotel_name,
        "lon": req.hotel_lon,
        "lat": req.hotel_lat,
        "tw": (req.hotel_tw_start, req.hotel_tw_end),
        "stay": 0,
    }
    spots = [
        {
            "name": s.name,
            "lon": s.lon,
            "lat": s.lat,
            "tw": (s.tw_start, s.tw_end),
            "stay": s.stay,
            "expected_arrival": s.expected_arrival,
        }
        for s in req.spots
    ]
    return {"hotel": hotel, "spots": spots}

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
                parsed = parse_biz_hours(biz_hours) if biz_hours else None
                tw_start = parsed[0] if parsed else None
                tw_end = parsed[1] if parsed else None
                items.append(POILookupItem(
                    name=actual_name, lon=lon, lat=lat, address=address,
                    tw_start=tw_start, tw_end=tw_end,
                ))
        except Exception:
            traceback.print_exc()
            failed.append(f"未在{req.city}找到{name}，请尝试更换搜索词")

    return POILookupResponse(items=items, failed=failed)

# ---------- 规划相关 ----------

@router.post("/api/suggest")
async def suggest(req: PlanRequest):
    """获取方案建议列表。

    不指定 n_days，run_planning 内部回退到 ca_suggest()，
    遍历多种聚类方法 × 天数，返回建议列表。
    响应中附带 cost_matrix/dist_matrix/polylines，供后续深度规划复用。

    Returns:
        dict: 含 suggestions（建议列表）、algo_time、cost_matrix、dist_matrix、
        polylines、amap_api_key、amap_security_code。

    Raises:
        HTTPException 500: 建议搜索引擎内部错误。
    """
    try:
        poi_cache = _build_poi_cache(req)
        result = run_planning(
            poi_cache, req.city, req.hotel_name,
            penalty_weight=req.penalty_weight,
            early_wait_weight=req.early_wait_weight,
            late_return_weight=req.late_return_weight,
            mode="fast",
            n_days=None,
            day_start=req.day_start,
            min_days=req.min_days,
        )
        result["amap_api_key"] = AMAP_JS_KEY
        result["amap_security_code"] = AMAP_JS_SECURITY_CODE
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/plan")
async def plan(req: PlanRequest):
    """执行完整规划，返回每日行程与高德地图可视化数据。

    n_days 为必填，mode 可选 "fast"(CA) 或 "deep"(VNS)。
    若 req 携带 cost_matrix/dist_matrix（来自 suggest 响应），
    则将矩阵作为 override 传给 run_planning，跳过驾车 API 调用。

    Returns:
        dict: 含 solution、best_days、daily_schedules、cost_matrix、dist_matrix、
        polylines、commentary、amap_api_key、amap_security_code。

    Raises:
        HTTPException 400: n_days 未指定时。
        HTTPException 500: 规划引擎内部错误。
    """
    if req.n_days is None:
        raise HTTPException(status_code=400, detail="n_days is required for planning")
    try:
        poi_cache = _build_poi_cache(req)
        result = run_planning(
            poi_cache, req.city, req.hotel_name,
            penalty_weight=req.penalty_weight,
            early_wait_weight=req.early_wait_weight,
            late_return_weight=req.late_return_weight,
            mode=req.mode,
            n_days=req.n_days,
            day_start=req.day_start,
            cost_matrix_override=req.cost_matrix,
            dist_matrix_override=req.dist_matrix,
        )
        result["amap_api_key"] = AMAP_JS_KEY
        result["amap_security_code"] = AMAP_JS_SECURITY_CODE
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))



# ---------- Agent 对话 ----------

@router.post("/api/chat")
async def chat(req: ChatRequest):
    """LLM Agent 对话接口，SSE 流式输出。

    Mock 模式返回死 token，方便前端联调。
    正式上线后设置 MOCK_MODE=False 即可切换 DeepSeek 真实调用。

    Raises:
        HTTPException 500: LLM 调用异常或数据格式错误。
    """
    try:
        messages = build_chat_messages(req.message, req.plan_result)

        async def _stream():
            # 第一阶段：非流式调用检测工具意图
            from openai import OpenAI

            from backend.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
            client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
            resp = client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=1024,
            )
            choice = resp.choices[0]
            if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
                messages.append(choice.message)
                for tc in choice.message.tool_calls:
                    tool_name = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments)
                    except Exception:
                        args = {}
                    tool_fn = TOOL_REGISTRY.get(tool_name)
                    if tool_fn:
                        yield f"data: {json.dumps({'type': 'tool_status', 'data': f'正在查询{tool_name}...'})}\n\n"
                        result = tool_fn(**args)
                        yield f"data: {json.dumps({'type': 'tool_result', 'data': result})}\n\n"
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(result, ensure_ascii=False),
                        })
                # 第二阶段：流式输出 LLM 回复
                try:
                    async for token in chat_stream(messages):
                        yield f"data: {json.dumps({'type': 'content', 'data': token})}\n\n"
                except Exception:
                    yield f"data: {json.dumps({'type': 'error', 'data': '对话生成失败，请重试'})}\n\n"
            else:
                # 无工具调用，直接流式输出
                try:
                    async for token in chat_stream(messages):
                        yield f"data: {json.dumps({'type': 'content', 'data': token})}\n\n"
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

    q = (
        select(HistoryRecord)
        .order_by(HistoryRecord.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await session.execute(q)).scalars().all()

    items = [
        HistorySummary(
            id=str(r.id),
            city=r.city,
            hotel=r.hotel,
            n_days=r.n_days,
            cost=r.cost,
            spot_count=r.spot_count,
            note=r.note,
            created_at=r.created_at.isoformat() if r.created_at else "",
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
        city=r.city,
        hotel=r.hotel,
        n_days=r.n_days,
        cost=r.cost,
        spot_count=r.spot_count,
        note=r.note,
        plan_result=r.plan_result,
        request_params=r.request_params,
        created_at=r.created_at.isoformat() if r.created_at else "",
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
    if r.device_id and r.device_id != req.device_id:
        raise HTTPException(status_code=403, detail="无权删除此记录")
    await session.delete(r)
    await session.commit()
    return {"ok": True}


