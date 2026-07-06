"""Agent 工具函数：营业时间 LLM 解析。"""
from datetime import datetime
from openai import OpenAI
from backend.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

_HOLIDAYS_AVAILABLE = False
try:
    import holidays
    _HOLIDAYS_AVAILABLE = True
except ImportError:
    pass


def _get_date_context() -> str:
    """返回当前日期上下文：日期、星期、是否中国法定节假日。"""
    now = datetime.now()
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekday = weekday_names[now.weekday()]
    is_holiday = False
    holiday_name = ""

    if _HOLIDAYS_AVAILABLE:
        cn_holidays = holidays.country_holidays("CN", years=now.year)
        if now.date() in cn_holidays:
            is_holiday = True
            holiday_name = cn_holidays.get(now.date())

    parts = [f"当前日期：{now.strftime('%Y-%m-%d')}（{weekday}）"]
    if is_holiday:
        parts.append(f"当日为法定节假日：{holiday_name}")
    if now.weekday() >= 5:
        parts.append("当日为周末")
    return "；".join(parts)


_PARSE_PROMPT = (
    "你是一个营业时间解析助手。\n"
    "高德地图 POI 的 opentime2 字段可能包含以下任意格式：\n"
    '- 简单格式："08:30-17:00"\n'
    '- 含日期段："04/01-10/31 周二-周日 08:30-17:00；11/01-03/31 08:30-16:30"\n'
    '- 含节假日："春节,劳动节 08:30-17:00"\n'
    '- 含闭馆日："周一 全天不开放"\n'
    '- 含停止入园时间："停止入园时间16:00"\n'
    '- 含说明文字："节假日营业时间以官方通知为准"\n'
    '- opentime2 可能为空或不存在\n\n'
    "{date_context}\n\n"
    "请根据当前日期提取最适合今天的最晚营业时间范围：\n"
    "1. 日期在前时忽略日期段，只看时间段（如 08:30-17:00）\n"
    "2. 如果今天闭馆，返回 null\n"
    "3. 如果 opentime2 为空或不存在，返回 null\n"
    "4. 只返回 JSON（不要 markdown）：{{\"start\": 分钟数, \"end\": 分钟数}} 或 null\n"
    "5. 分钟数以午夜 00:00 为基准，如 08:00=480, 17:00=1020\n\n"
    "opentime2：{opentime2}"
)


def parse_biz_hours(opentime2: str) -> tuple[int, int] | None:
    """LLM 解析高德 opentime2 营业时间。

    Args:
        opentime2: 高德 API 返回的原始 opentime2 字符串。

    Returns:
        (start_min, end_min) 或 None（解析失败时）。
    """
    if not opentime2 or not opentime2.strip():
        return None

    date_context = _get_date_context()
    prompt = _PARSE_PROMPT.format(date_context=date_context, opentime2=opentime2)

    try:
        client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=128,
        )
        text = resp.choices[0].message.content.strip()
        import json
        data = json.loads(text)
        if data is not None:
            start = int(data["start"])
            end = int(data["end"])
            if 0 <= start < end <= 1440:
                return (start, end)
    except Exception:
        pass
    return None
