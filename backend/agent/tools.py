"""Agent 工具函数：营业时间 LLM 解析 + 对话消息构建。"""
import asyncio
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
    "5. 分钟数以午夜 00:00 为基准，如 08:00=480, 17:00=1020\n"
    "6. 跨午夜营业时间（如 22:00-02:00）截断到当天 24:00，即 end=1440\n\n"
    "opentime2：{opentime2}"
)


_CHAT_SYSTEM = (
    "你是一个旅行伴侣，正在陪用户一起规划旅行。\n"
    "核心原则：\n"
    "1. 用简短的口语回复，像朋友聊天一样自然\n"
    "2. 不要帮用户计算路径或规划行程——这不是你需要做的\n"
    "3. 用户可能需要陪伴、建议或讨论想法，倾听就好\n"
    "4. 如果用户问起当前的规划方案，可以参考提供的规划上下文来回应\n"
    "5. 永远不要说你在「作为AI助手」——你就是旅行伴侣本人\n"
    "6. 如果用户的问题超出了旅行范围，温和地引导回旅行话题"
)


def build_chat_messages(message: str, plan_result: dict | None = None) -> list[dict]:
    """构建对话消息列表。

    Args:
        message: 用户输入的消息。
        plan_result: 可选的规划结果，注入 system prompt 作为上下文。

    Returns:
        OpenAI-compatible messages 列表。
    """
    system = _CHAT_SYSTEM
    if plan_result:
        import json
        summary = {
            "city": plan_result.get("city", "未知"),
            "n_days": plan_result.get("best_days", 0),
            "total_cost": plan_result.get("solution", {}).get("total_cost", 0),
            "commentary": plan_result.get("commentary", ""),
        }
        system += f"\n\n当前规划概要（供参考）：\n{json.dumps(summary, ensure_ascii=False)}"

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": message},
    ]


async def mock_stream_chat(messages: list[dict]):
    """Mock SSE 流式聊天，模拟 1 条自然回复用于联调。

    Args:
        messages: OpenAI-compatible 消息列表（Mock 模式实际不使用）。

    Yields:
        逐字符流式 token。
    """
    reply = "今天的安排不错，下午可以去附近的公园走走！"
    for char in reply:
        yield char
        await asyncio.sleep(0.05)


async def stream_chat(messages: list[dict]):
    """真实 DeepSeek SSE 流式聊天。

    Args:
        messages: OpenAI-compatible 消息列表（system + user）。

    Yields:
        DeepSeek 返回的内容 token。
    """
    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        stream=True,
        temperature=0.7,
        max_tokens=1024,
    )
    for chunk in resp:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta and delta.content:
            yield delta.content
            await asyncio.sleep(0)


MOCK_MODE = True


async def chat_stream(messages: list[dict]):
    """统一入口：MOCK_MODE=True 时模拟，否则调 DeepSeek。

    Args:
        messages: OpenAI-compatible 消息列表。

    Yields:
        逐字符或逐 token 流式输出。
    """
    if MOCK_MODE:
        async for token in mock_stream_chat(messages):
            yield token
    else:
        async for token in stream_chat(messages):
            yield token


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
