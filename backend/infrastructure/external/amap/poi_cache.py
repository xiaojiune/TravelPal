"""POI 查询缓存：高德整份响应 + LLM 营业时间解析的单一缓存。

设计说明（对齐 architecture.md 轴 4 缓存策略 + Rule of Three）：
- POI 查询（get_poi_details）一次高德调用返回 {坐标/地址/营业时间原文/分类}，营业时间
  tw_start/tw_end 由 parse_biz_hours（LLM）基于同一份营业时间原文解析得到——两者一一对应、
  同一时刻产生，解析结果是高德响应的纯派生。故**合并为一个缓存、一个 TTL**，不拆两层
  （拆两层只会引入"L1 命中但 L2 过期→再解析一次"的复杂度，无额外收益）。
- 命中即免高德 API + 免 LLM 解析（零外部调用）；miss 才走高德 + LLM，写回后复用。
- 与 driving_cache 同模式：Redis 懒连接 + 不可用时静默降级（未命中/丢弃写入），不阻塞主流程。
- Redis 不可用 => get_poi_cached 返回 None（调用方走原逻辑），set 丢弃写入。
"""

import hashlib
import json
from typing import Any

from backend.config import settings

# POI 缓存 TTL（秒）：24 小时。营业时间时效为主（商户变更一天内可能用旧值），
# 坐标/地址虽更久但捆绑在同一份响应里，只能跟着营业时间走。
_POI_TTL = 24 * 60 * 60

_client: Any | None = None


def _get_redis():
    """懒初始化同步 Redis 客户端（decode_responses 直接得 str）。

    Returns:
        redis.Redis | None: 客户端；连接失败返回 None（降级）。
    """
    global _client
    if _client is None:
        try:
            import redis

            _client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        except Exception:
            _client = None
    return _client


def poi_key(city: str, name: str) -> str:
    """构造 POI 缓存键（名称规范化后 sha1 指纹，跨会话可复用）。

    Args:
        city: 所在城市。
        name: POI 名称（原样，键内指纹已规范化）。

    Returns:
        str: Redis 键 `tp:poi:{city}:{fp}`；fp 为规范化名称的 sha1 前 16 位。
    """
    from backend.infrastructure.external.amap.amap_loader import normalize_text

    norm = normalize_text(name)
    fp = hashlib.sha1(norm.encode("utf-8")).hexdigest()[:16]
    return f"tp:poi:{city}:{fp}"


def get_poi_cached(city: str, name: str) -> dict | None:
    """读取单个 POI 的完整查询结果缓存。

    Args:
        city: 所在城市。
        name: POI 名称。

    Returns:
        dict | None: {name, lon, lat, address, tw_start, tw_end, poi_type}；
            未命中或 Redis 不可用时返回 None。
    """
    client = _get_redis()
    if client is None:
        return None
    try:
        raw = client.get(poi_key(city, name))
        if raw is None:
            return None
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def set_poi_cached(city: str, name: str, data: dict) -> None:
    """写入单个 POI 的完整查询结果缓存（TTL 24h 固定）。

    Args:
        city: 所在城市。
        name: POI 名称。
        data: {name, lon, lat, address, tw_start, tw_end, poi_type}。
    """
    client = _get_redis()
    if client is None:
        return
    try:
        client.set(poi_key(city, name), json.dumps(data, ensure_ascii=False), ex=_POI_TTL)
    except Exception:
        pass
