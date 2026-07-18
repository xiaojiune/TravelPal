"""POI 工具：营业时间 LLM 解析 + POI 查询 Function Calling。"""

import json
from openai import OpenAI
from backend.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from backend.agent.tools.prompts import build_date_context, PARSE_PROMPT


def poi_lookup(city: str, name: str) -> dict:
    """通过高德 API 查询 POI 的坐标、地址和营业时间。

    Args:
        city: 所在城市。
        name: POI 名称。

    Returns:
        dict: { name, lon, lat, address, tw_start, tw_end }
        查询失败时返回 { error: str }。
    """
    from backend.data.amap_loader import get_poi_details
    try:
        result = get_poi_details(name, city)
        if isinstance(result, str):
            return {"error": result}
        lon, lat, biz_hours, address, _, _, actual_name = result
        parsed = parse_biz_hours(biz_hours) if biz_hours else None
        return {
            "name": actual_name,
            "lon": lon,
            "lat": lat,
            "address": address,
            "tw_start": parsed[0] if parsed else None,
            "tw_end": parsed[1] if parsed else None,
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
