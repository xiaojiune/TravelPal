"""驾车路径点对缓存：复用高德驾车 API 结果，避免重复拉取。

设计（对齐 add_poi 增量需求）：
- 缓存粒度 = 点对（起点→终点），而非整矩阵。增量天然成立：多次 add 不同点时，
  每对独立命中/过期，已拉过的对直接复用。
- 键结构 `tp:driving:{city}:{start_fp}:{end_fp}`；点指纹 = 规范化
  `name|lon|lat` 的 sha1 前 16 位（同一坐标即视为同一点，跨会话可复用）。
- 值 = JSON {duration_min, distance_km, polyline?}；TTL 固定 600s（10 分钟）。
- 缓存一致性由点集合变化驱动（新点 → 新对 → 新键），无手动失效。
- 同步接口：adjust_plan（Celery worker 同步上下文）与工具（async 内调用）
  两端共用一份实现；Redis 调用毫秒级阻塞可接受。
- 降级策略：Redis 不可用时静默降级为「未命中/丢弃写入」，不阻塞主流程
  （add_poi 退回现场拉取驾车 API）。
"""

import hashlib
import json
from typing import Any

from backend.config import settings

# 点对缓存 TTL（秒），固定 10 分钟；驾车数据时效内可安全复用
_DRIVING_TTL = 600

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


def point_fingerprint(name: str, lon: float, lat: float) -> str:
    """计算单个点的规范化指纹（跨会话可复用的缓存键段）。

    Args:
        name: 点名称。
        lon: 经度（GCJ-02）。
        lat: 纬度（GCJ-02）。

    Returns:
        str: sha1("name|lon|lat") 前 16 位十六进制。
    """
    raw = f"{name}|{lon:.6f}|{lat:.6f}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def pair_key(city: str, origin: dict, destination: dict) -> str:
    """构造点对缓存键（方向敏感：驾车 A→B 与 B→A 耗时不同）。

    Args:
        city: 所在城市。
        origin: 起点 {name, lon, lat}。
        destination: 终点 {name, lon, lat}。

    Returns:
        str: Redis 键 `tp:driving:{city}:{start_fp}:{end_fp}`。
    """
    start_fp = point_fingerprint(origin["name"], origin["lon"], origin["lat"])
    end_fp = point_fingerprint(destination["name"], destination["lon"], destination["lat"])
    return f"tp:driving:{city}:{start_fp}:{end_fp}"


def get_driving_pair(city: str, origin: dict, destination: dict) -> dict | None:
    """读取一对点（方向敏感）的驾车数据缓存。

    Args:
        city: 所在城市。
        origin: 起点 {name, lon, lat}。
        destination: 终点 {name, lon, lat}。

    Returns:
        dict | None: {duration_min, distance_km, polyline?}；未命中或 Redis 不可用时返回 None。
    """
    client = _get_redis()
    if client is None:
        return None
    try:
        raw = client.get(pair_key(city, origin, destination))
        if raw is None:
            return None
        return json.loads(raw)
    except Exception:
        return None


def set_driving_pair(city: str, origin: dict, destination: dict, data: dict) -> None:
    """写入一对点的驾车数据缓存（TTL 600s 固定）。

    Args:
        city: 所在城市。
        origin: 起点 {name, lon, lat}。
        destination: 终点 {name, lon, lat}。
        data: {duration_min, distance_km, polyline?}。
    """
    client = _get_redis()
    if client is None:
        return
    try:
        client.set(pair_key(city, origin, destination), json.dumps(data, ensure_ascii=False), ex=_DRIVING_TTL)
    except Exception:
        pass
