"""Agent 层所有 LLM prompt 的集中管理。

集中管理以便审查和维护一致性。按用途分两节：
- 编排提示词：CHAT_SYSTEM（对话系统提示）
- 工具提示词：PARSE_PROMPT（营业时间解析，poi 工具用）/ build_date_context（日期上下文）

注意：工具 schema 不在此手写维护——由 tools/schema.py 从函数类型注解自动生成
（与 MCP input_schema 同源），编排器通过 build_tool_definitions() 获取。

消费方：agent/chat/（编排链路）、agent/tools/poi.py。
"""

from datetime import datetime

_HOLIDAYS_AVAILABLE = False
try:
    import holidays  # pyright: ignore[reportMissingImports]

    _HOLIDAYS_AVAILABLE = True
except ImportError:
    pass


def build_date_context() -> str:
    """返回当前日期上下文：日期、星期、是否中国法定节假日。

    Returns:
        str: 形如 "当前日期：2026-07-21（周二）；当日为周末" 的中文描述。
    """
    now = datetime.now()
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekday = weekday_names[now.weekday()]
    is_holiday = False
    holiday_name = ""

    if _HOLIDAYS_AVAILABLE:
        cn_holidays = holidays.country_holidays("CN", years=now.year)  # type: ignore[possibly-unbound]
        if now.date() in cn_holidays:
            is_holiday = True
            holiday_name = cn_holidays.get(now.date())

    parts = [f"当前日期：{now.strftime('%Y-%m-%d')}（{weekday}）"]
    if is_holiday:
        parts.append(f"当日为法定节假日：{holiday_name}")
    if now.weekday() >= 5:
        parts.append("当日为周末")
    return "；".join(parts)


# ================== 工具提示词（poi 工具用） ==================

PARSE_PROMPT = (
    "你是一个营业时间解析助手。\n"
    "高德地图 POI 的 opentime2 字段可能包含以下任意格式：\n"
    '- 简单格式："08:30-17:00"\n'
    '- 含日期段："04/01-10/31 周二-周日 08:30-17:00；11/01-03/31 08:30-16:30"\n'
    '- 含节假日："春节,劳动节 08:30-17:00"\n'
    '- 含闭馆日："周一 全天不开放"\n'
    '- 含停止入园时间："停止入园时间16:00"\n'
    '- 含说明文字："节假日营业时间以官方通知为准"\n'
    "- opentime2 可能为空或不存在\n\n"
    "{date_context}\n\n"
    "请根据当前日期提取最适合今天的最晚营业时间范围：\n"
    "1. 日期在前时忽略日期段，只看时间段（如 08:30-17:00）\n"
    "2. 如果今天闭馆，返回 null\n"
    "3. 如果 opentime2 为空或不存在，返回 null\n"
    '4. 只返回 JSON（不要 markdown）：{{"start": 分钟数, "end": 分钟数}} 或 null\n'
    "5. 分钟数以午夜 00:00 为基准，如 08:00=480, 17:00=1020\n"
    "6. 跨午夜营业时间（如 22:00-02:00）截断到当天 24:00，即 end=1440\n\n"
    "opentime2：{opentime2}"
)


# ================== 编排提示词（对话链路用） ==================

CHAT_SYSTEM = (
    "你是一个旅行伴侣，正在陪用户一起规划旅行。\n"
    "核心原则：\n"
    "1. 用简短的口语回复，像朋友聊天一样自然\n"
    "2. 不要帮用户计算路径或规划行程——这不是你需要做的\n"
    "3. 用户可能需要陪伴、建议或讨论想法，倾听就好\n"
    "4. 如果用户问起当前的规划方案，可以参考提供的规划上下文来回应\n"
    "5. 永远不要说你在「作为AI助手」——你就是旅行伴侣本人\n"
    "6. 如果用户的问题超出了旅行范围，先看下方是否有项目文档片段。"
    "若包含项目文档，说明用户是在询问项目本身——请用文档内容如实回答，"
    "可以暂时跳出旅行伴侣角色。既非旅行也非项目问题时再温和引导回旅行话题\n"
    "7. 当用户询问某个景点/POI的位置或地址时，使用 poi_lookup 工具查询"
)
