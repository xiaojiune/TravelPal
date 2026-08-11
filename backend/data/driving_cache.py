"""驾车路径缓存：点对基元 + 整矩阵快照。

两层设计（对齐 ADR-008 轴 4 缓存策略）：
- 点对缓存（本文件下半部）：键 `tp:driving:{city}:{start_fp}:{end_fp}`，TTL 600s，
  增量操作层（add_poi 场景按点对命中/过期）。驾车 A→B 与 B→A 耗时不同，方向敏感。
- 矩阵快照（本文件上半部）：键 `tp:matrix:{city}:{points_fp}`，TTL 7200s 滑动续期，
  读加速层（run_planning 整矩阵直接复用）。驾车成本与排序/天数无关（cost[i][j] 只由
  坐标决定），快照按点集合指纹存取；单日/全部重排共享同一份矩阵。
  快照值 {cost, dist, polylines} 是同一次 build_real_data 的产物，绑定缓存保证原子性。

- 点指纹 = 规范化 `name|lon|lat` 的 sha1 前 16 位（同一坐标即视为同一点，跨会话可复用）；
  坐标进指纹，点集合变化天然失效传播（无需索引表）。
- 同步接口：adjust_plan（Celery worker 同步上下文）与工具（async 内调用）两端共用。
- 降级策略：Redis 不可用时静默降级为「未命中/丢弃写入」，不阻塞主流程。
"""

import hashlib
import json
from typing import Any

from backend.config import settings

# 点对缓存 TTL（秒），固定 10 分钟；驾车数据时效内可安全复用
_DRIVING_TTL = 600
# 矩阵快照 TTL（秒），2 小时滑动续期：活跃批点持续续命，冷批点自然淘汰
_MATRIX_TTL = 7200

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


# ================== 矩阵快照 ==================


def matrix_key(city: str, poi_names: list[str], coords: list[tuple[float, float]]) -> str:
    """构造矩阵快照键（点集合指纹：有序全部点拼接后 sha1）。

    Args:
        city: 所在城市。
        poi_names: 点名称列表（含酒店，索引 0）。
        coords: 坐标列表，与 poi_names 一一对应。

    Returns:
        str: Redis 键 `tp:matrix:{city}:{fp}`。
    """
    parts = "|".join(f"{n}|{lon:.6f}|{lat:.6f}" for n, (lon, lat) in zip(poi_names, coords))
    fp = hashlib.sha1(parts.encode("utf-8")).hexdigest()[:16]
    return f"tp:matrix:{city}:{fp}"


def get_driving_matrix(city: str, poi_names: list[str], coords: list[tuple[float, float]]) -> dict | None:
    """读取整矩阵快照（命中时滑动续期 TTL）。

    Args:
        city: 所在城市。
        poi_names: 点名称列表（含酒店，索引 0）。
        coords: 坐标列表，与 poi_names 一一对应。

    Returns:
        dict | None: {cost: [[..]], dist: [[..]], polylines: {"i_j": poly}}；
            未命中或 Redis 不可用时返回 None。
    """
    client = _get_redis()
    if client is None:
        return None
    try:
        key = matrix_key(city, poi_names, coords)
        raw = client.get(key)
        if raw is None:
            return None
        client.expire(key, _MATRIX_TTL)
        return json.loads(raw)
    except Exception:
        return None


def set_driving_matrix(city: str, poi_names: list[str], coords: list[tuple[float, float]], data: dict) -> None:
    """写入整矩阵快照（TTL 7200s 固定，命中后由 get_driving_matrix 续期）。

    Args:
        city: 所在城市。
        poi_names: 点名称列表（含酒店，索引 0）。
        coords: 坐标列表，与 poi_names 一一对应。
        data: {cost: [[..]], dist: [[..]], polylines: {"i_j": poly}}。
    """
    client = _get_redis()
    if client is None:
        return
    try:
        key = matrix_key(city, poi_names, coords)
        client.set(key, json.dumps(data, ensure_ascii=False), ex=_MATRIX_TTL)
    except Exception:
        pass


# ================== 点对缓存 ==================


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
