"""FastAPI 路由定义：POI 查询、行程规划、Agent 对话。"""

import json
import traceback
from fastapi import APIRouter, HTTPException
from backend.api.schemas import PlanRequest, POILookupRequest, POILookupResponse, POILookupItem, ChatRequest
from backend.engine.pipeline import run_planning
from backend.data.amap_loader import get_poi_details
from backend.config import AMAP_API_KEY
from backend.agent.tools import parse_biz_hours, build_chat_messages, chat_stream
from fastapi.responses import StreamingResponse

router = APIRouter()

# ================== 辅助函数 ==================

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
    """
    items: list[POILookupItem] = []
    failed: list[str] = []

    for name in req.names:
        try:
            result = get_poi_details(name, req.city)
            if isinstance(result, str):
                failed.append(result)
            else:
                lon, lat, biz_hours, address, pname, cityname, actual_name = result
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
    遍历多种聚类方法 × 天数，返回 top-5 建议。
    响应中附带 cost_matrix/dist_matrix，供后续深度规划
    复用以跳过驾车 API 调用。

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
        result["amap_api_key"] = AMAP_API_KEY
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
        result["amap_api_key"] = AMAP_API_KEY
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
            """SSE 生成器：逐 token 推送 chat_stream 输出，最后发 done 信号。"""
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


