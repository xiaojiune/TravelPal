"""驾车路径工具：轻量两点驾车查询，供 AI 问答"A到B耗时多久"。

架构预留说明：当前仅支持驾车（高德 direction/driving API）。
后期若融合步行/骑车/公交，在此文件新增对应包装函数（如
get_walking/get_bicycling/get_transit），复用 amap_loader 新增的
私有函数，TOOL_REGISTRY 增项即可，不破坏现有契约。
"""

from backend.data.amap_loader import _get_driving_data


def get_driving(origin: dict, destination: dict) -> dict:
    """查询两点间驾车距离与耗时。

    Args:
        origin: {"name": str, "lon": float, "lat": float} 起点。
        destination: {"name": str, "lon": float, "lat": float} 终点。

    Returns:
        {"origin_name": str, "destination_name": str, "distance_km": float, "duration_min": float}；
        失败返回 {"error": str}。折线待以后扩展，当前不返回。
    """
    try:
        origin_name = origin.get("name", "起点")
        destination_name = destination.get("name", "终点")
        result = _get_driving_data(
            (origin["lon"], origin["lat"]),
            (destination["lon"], destination["lat"]),
        )
        d_km, dur_s, _ = result if result else (None, None, None)
        if d_km is None or dur_s is None:
            return {"error": f"'{origin_name}' 到 '{destination_name}' 驾车查询失败"}
        return {
            "origin_name": origin_name,
            "destination_name": destination_name,
            "distance_km": round(d_km, 2),
            "duration_min": round(dur_s / 60.0, 1),
        }
    except Exception as e:
        origin_name = origin.get("name", "起点")
        destination_name = destination.get("name", "终点")
        return {"error": f"'{origin_name}' 到 '{destination_name}' 驾车查询失败: {e}"}
