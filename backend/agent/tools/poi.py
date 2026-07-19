"""POI 工具：营业时间 LLM 解析 + POI 查询 Function Calling。"""

import json

from openai import OpenAI

from backend.agent.tools.prompts import PARSE_PROMPT, build_date_context
from backend.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


def _classify_poi(poi_type: str, name: str) -> str:
    """根据高德行业分类和名称判定 POI 类型。

    Returns:
        "hotel" | "spot" | "unknown"
    """
    type_lower = poi_type.lower()
    if "住宿服务" in type_lower or "酒店" in type_lower or "宾馆" in type_lower or "民宿" in type_lower:
        return "hotel"
    name_lower = name.lower()
    if any(kw in name_lower for kw in ["酒店", "宾馆", "公寓", "民宿"]):
        return "hotel"
    return "spot"


def poi_lookup(city: str, name: str) -> dict:
    """通过高德 API 查询 POI 的坐标、地址和营业时间。

    自动识别 POI 类型（酒店/景点），酒店默认时间窗为 0-1440（全天）。

    Args:
        city: 所在城市。
        name: POI 名称。

    Returns:
        dict: { name, lon, lat, address, tw_start, tw_end, poi_type }
        poi_type 为 "hotel" | "spot" | "unknown"。
        查询失败时返回 { error: str }。
    """
    from backend.data.amap_loader import get_poi_details
    try:
        result = get_poi_details(name, city)
        if isinstance(result, str):
            return {"error": result}
        lon, lat, biz_hours, address, _, _, actual_name, poi_type_str = result
        poi_type = _classify_poi(poi_type_str, actual_name)
        parsed = parse_biz_hours(biz_hours) if biz_hours else None
        if poi_type == "hotel":
            tw_start = 0
            tw_end = 1440
        else:
            tw_start = parsed[0] if parsed else 480
            tw_end = parsed[1] if parsed else 1020
        return {
            "name": actual_name,
            "lon": lon,
            "lat": lat,
            "address": address,
            "tw_start": tw_start,
            "tw_end": tw_end,
            "poi_type": poi_type,
        }
    except Exception as e:
        return {"error": str(e)}


def parse_biz_hours(opentime2: str) -> tuple[int, int] | None:
    """LLM 解析高德 opentime2 营业时间。

    Args:
        opentime2: 高德 API 返回的原始 opentime2 字符串。

    Returns:
        (start_min, end_min) 或 None（解析失败时）。
    """
    if not opentime2 or not opentime2.strip():
        return None

    date_context = build_date_context()
    prompt = PARSE_PROMPT.format(date_context=date_context, opentime2=opentime2)

    try:
        client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=128,
        )
        text = resp.choices[0].message.content.strip()
        data = json.loads(text)
        if data is not None:
            start = int(data["start"])
            end = int(data["end"])
            if 0 <= start < end <= 1440:
                return (start, end)
    except Exception:
        pass
    return None
