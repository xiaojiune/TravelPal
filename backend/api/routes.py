import json
import traceback
from fastapi import APIRouter, HTTPException
from backend.api.schemas import PlanRequest, PlanAdjustRequest, POILookupRequest, POILookupResponse, POILookupItem, ChatRequest
from backend.engine.pipeline import run_planning, adjust_plan
from backend.data.amap_loader import get_poi_details
from backend.config import AMAP_API_KEY
from backend.agent.tools import parse_biz_hours, build_chat_messages, chat_stream
from fastapi.responses import StreamingResponse

router = APIRouter()


def _build_poi_cache(req: PlanRequest):
    """将 PlanRequest 转换为 run_planning 所需的 poi_cache 格式。

    前端传来的坐标数据可直接映射，无需额外转换。
    时间窗以 (start, end) 元组形式传递。
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
        }
        for s in req.spots
    ]
    return {"hotel": hotel, "spots": spots}


@router.post("/api/poi-lookup", response_model=POILookupResponse)
async def poi_lookup(req: POILookupRequest):
    """批量查询 POI 坐标和地址。

    前端传入城市 + 名称列表，后端调用高德 POI 搜索 API，
    返回每个名称的坐标和地址。未找到的名称列入 failed 列表。
    """
    items: list[POILookupItem] = []
    failed: list[str] = []

    for name in req.names:
        try:
            lon, lat, biz_hours, address = get_poi_details(name, req.city)
            # 高德返回默认坐标 (116.4, 39.9) 时视为未找到
            if abs(lon - 116.4) < 0.01 and abs(lat - 39.9) < 0.01:
                failed.append(name)
            else:
                parsed = parse_biz_hours(biz_hours) if biz_hours else None
                tw_start = parsed[0] if parsed else None
                tw_end = parsed[1] if parsed else None
                items.append(POILookupItem(
                    name=name, lon=lon, lat=lat, address=address,
                    tw_start=tw_start, tw_end=tw_end,
                ))
        except Exception:
            failed.append(name)

    return POILookupResponse(items=items, failed=failed)


@router.post("/api/suggest")
async def suggest(req: PlanRequest):
    """获取方案建议列表。

    不指定 n_days，run_planning 内部回退到 ca_suggest()，
    遍历多种聚类方法 × 天数，返回 top-5 建议。
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
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/plan")
async def plan(req: PlanRequest):
    """执行完整规划，返回 3D 地图 HTML 和每日行程。

    n_days 为必填，mode 可选 "fast"(CA) 或 "deep"(VNS)。
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
        )
        result["amap_api_key"] = AMAP_API_KEY
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/chat")
async def chat(req: ChatRequest):
    """LLM Agent 对话接口，SSE 流式输出。

    Mock 模式返回死 token，方便前端联调。
    正式上线后设置 MOCK_MODE=False 即可切换 DeepSeek 真实调用。
    """
    try:
        messages = build_chat_messages(req.message, req.plan_result)

        async def _stream():
            async for token in chat_stream(messages):
                yield f"data: {json.dumps({'type': 'content', 'data': token})}\n\n"
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


@router.patch("/api/plan/adjust")
async def plan_adjust(req: PlanAdjustRequest):
    """调整已有方案（均衡、改天数等）。

    接收当前方案状态，按 adjustments 指令重新求解后返回新方案。
    """
    try:
        result = adjust_plan(
            req.spots, req.cost_matrix, req.dist_matrix,
            req.routes, req.adjustments,
        )
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
