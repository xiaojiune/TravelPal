"""POI 工具：营业时间 LLM 解析 + POI 查询 Function Calling + 停留时间推断。"""

import json

from backend.agent.prompts import PARSE_PROMPT, build_date_context
from backend.infrastructure.llm.factory import get_llm_service

# 停留时间兜底映射：设施/景点类型 → 默认停留分钟数（LLM 推断失败的降级）
# 关键词优先、poi_type 次之、最后兜底；酒店为 depot 不参与（调用方跳过）
_STAY_FALLBACK = {
    "餐饮": 60,
    "咖啡": 45,
    "购物": 90,
    "娱乐": 90,
    "公园": 90,
    "博物馆": 120,
    "展览": 120,
    "寺庙": 60,
    "地标": 60,
    "交通": 30,
}
_STAY_DEFAULT = 90


def _classify_poi(poi_type: str, name: str) -> str:
    """根据高德行业分类和名称判定 POI 类型。

    除酒店（原点）与景点（行程点）外，将餐饮/购物/娱乐等设施识别为 facility
    （同样是行程点，支持「万物可量化」：任何可搜索的实体都可进入行程）。

    Args:
        poi_type: 高德行业分类字符串（如 "住宿服务;宾馆酒店"）。
        name: POI 名称，辅助判定。

    Returns:
        "hotel" | "spot" | "facility" | "unknown"
    """
    type_lower = poi_type.lower()
    if "住宿服务" in type_lower or "酒店" in type_lower or "宾馆" in type_lower or "民宿" in type_lower:
        return "hotel"
    name_lower = name.lower()
    if any(kw in name_lower for kw in ["酒店", "宾馆", "公寓", "民宿"]):
        return "hotel"
    # 设施类：餐饮/购物/休闲娱乐/生活服务等 → facility（行程点，非酒店原点）
    if any(kw in type_lower for kw in ["餐饮", "购物", "休闲娱乐", "生活服务", "医疗", "金融", "汽车", "交通设施"]):
        return "facility"
    if any(kw in name_lower for kw in ["餐厅", "饭店", "食堂", "咖啡", "火锅", "烧烤", "商场", "超市", "便利店"]):
        return "facility"
    return "spot"


async def poi_lookup(city: str, names: list[str]) -> list[dict]:
    """批量通过高德 API 查询 POI 的坐标、地址和营业时间。

    自动识别每个 POI 类型（酒店/景点），酒店默认时间窗为 0-1440（全天）。
    内部 LLM 解析（parse_biz_hours）走 domain/LLMService 防腐层。

    Args:
        city: 所在城市。
        names: POI 名称列表（酒店/景点）。

    Returns:
        list[dict]: 每项 { name, lon, lat, address, tw_start, tw_end, poi_type }
        poi_type 为 "hotel" | "spot" | "facility" | "unknown"。
        单个查询失败时该项为 { name, error: str }。
    """
    from backend.data.amap_loader import get_poi_details

    results: list[dict] = []
    for name in names:
        try:
            result = get_poi_details(name, city)
            if isinstance(result, str):
                results.append({"name": name, "error": result})
                continue
            lon, lat, biz_hours, address, _, _, actual_name, poi_type_str = result
            poi_type = _classify_poi(poi_type_str, actual_name)
            parsed = await parse_biz_hours(biz_hours) if biz_hours else None
            if poi_type == "hotel":
                tw_start = 0
                tw_end = 1440
            else:
                tw_start = parsed[0] if parsed else 480
                tw_end = parsed[1] if parsed else 1020
            results.append(
                {
                    "name": actual_name,
                    "lon": lon,
                    "lat": lat,
                    "address": address,
                    "tw_start": tw_start,
                    "tw_end": tw_end,
                    "poi_type": poi_type,
                }
            )
        except Exception as e:
            results.append({"name": name, "error": str(e)})
    return results


async def estimate_stay(
    poi_type: str,
    name: str,
    context: str | None = None,
    explicit_stay: int | None = None,
) -> int:
    """推断 POI 建议停留时间（分钟），三层降级：显式参数 → LLM 推断 → 映射兜底。

    除酒店外所有点（景点/设施）都应有停留时间；酒店为 depot 不调用本函数。

    Args:
        poi_type: POI 类型（hotel/spot/facility）。
        name: POI 名称。
        context: 可选的对话上下文（用户偏好/意图），供 LLM 推断参考。
        explicit_stay: 显式传入的停留时间，优先采用（最优先）。

    Returns:
        int: 建议停留分钟数。
    """
    if explicit_stay is not None:
        return explicit_stay
    if context:
        try:
            service = get_llm_service()
            prompt = (
                "你是行程规划助手。根据 POI 类型与用户语境，给出建议停留时间（分钟，整数，30-240 之间）。"
                "只返回数字。\n"
                f"POI 类型：{poi_type}\nPOI 名称：{name}\n用户语境：{context}\n"
            )
            text = await service.complete_text(prompt, temperature=0.1, max_tokens=8)
            if text:
                stay = int(text.strip())
                if 30 <= stay <= 240:
                    return stay
        except Exception:
            pass
    for kw, minutes in _STAY_FALLBACK.items():
        if kw in name or kw in poi_type:
            return minutes
    return _STAY_DEFAULT


async def parse_biz_hours(opentime2: str) -> tuple[int, int] | None:
    """LLM 解析高德 opentime2 营业时间（经 LLMService 防腐层）。

    Args:
        opentime2: 高德 API 返回的原始 opentime2 字符串。

    Returns:
        (start_min, end_min) 或 None（解析失败时）。
    """
    if not opentime2:
        return None
    stripped = opentime2.strip()
    if not stripped:
        return None

    date_context = build_date_context()
    prompt = PARSE_PROMPT.format(date_context=date_context, opentime2=opentime2)

    service = get_llm_service()
    text = await service.complete_text(prompt, temperature=0.1, max_tokens=128)
    if text is None:
        return None
    try:
        data = json.loads(text)
        if data is not None:
            start = int(data["start"])
            end = int(data["end"])
            if 0 <= start < end <= 1440:
                return (start, end)
    except Exception:
        pass
    return None
