"""驾车数据服务：整矩阵 + 点对的获取统一入口（含缓存复用）。

把「查缓存 → 拉高德驾车 API → 写缓存」收口成两个明确语义，供 OR 编排层
（pipeline）依赖，使其不再直接耦合 amap_loader / driving_cache 的实现细节。
为未来可插拔数据提供者（多 travel_mode、多 API 键、ML 偏好上下文）预留边界。

依赖方向：pipeline → driving_service（data 层）；端口 DrivingDataProvider 定义在
domain/ports.py，本模块提供 AmapDrivingProvider 适配器实现它。
"""

from backend.domain.ports import DrivingDataProvider  # noqa: F401  # 端口在 domain/ports，本文件实现
from backend.infrastructure.data.amap_loader import _get_driving_data, build_real_data
from backend.infrastructure.data.driving_cache import (
    get_driving_matrix,
    get_driving_pair,
    set_driving_matrix,
    set_driving_pair,
)


class AmapDrivingProvider:  # 实现 DrivingDataProvider 端口
    """高德驾车数据提供者：包装 driving_service 实现，作为 DrivingDataProvider 默认适配器。"""

    def get_matrix(self, city: str, poi_names: list, coords: list, cancel_check=None) -> dict:
        return get_matrix(city, poi_names, coords, cancel_check)

    def get_pair(self, city: str, origin: dict, destination: dict) -> dict | None:
        return get_pair(city, origin, destination)

    def get_polyline(self, origin: tuple[float, float], destination: tuple[float, float]) -> str | None:
        return get_polyline(origin, destination)


def get_matrix(
    city: str,
    poi_names: list[str],
    coords: list[tuple[float, float]],
    cancel_check=None,
) -> dict:
    """获取完整驾车成本矩阵。

    缓存命中直接返回；未命中调 build_real_data 拉取并写入缓存。
    统一返回 {cost: [[..]], dist: [[..]], polylines: {(i, j): str}}——
    polylines 用 (int, int) 元组键，供 pipeline._supplement_polylines 直接使用。

    Args:
        city: 所在城市。
        poi_names: 点名称列表（含酒店，索引 0）。
        coords: 坐标列表，与 poi_names 一一对应。
        cancel_check: 取消检查回调（逐对拉取间探测，透传给 build_real_data）。

    Returns:
        dict: {cost, dist, polylines}。
    """
    snapshot = get_driving_matrix(city, poi_names, coords)
    if snapshot is not None:
        polylines = {
            (int(k.split("_")[0]), int(k.split("_")[1])): v
            for k, v in snapshot.get("polylines", {}).items()
        }
        return {"cost": snapshot["cost"], "dist": snapshot["dist"], "polylines": polylines}

    cost, dist, polylines = build_real_data(poi_names, coords, cancel_check=cancel_check)
    data = {
        "cost": cost.tolist(),
        "dist": dist.tolist(),
        "polylines": {f"{k[0]}_{k[1]}": v for k, v in polylines.items()},
    }
    set_driving_matrix(city, poi_names, coords, data)
    return {"cost": data["cost"], "dist": data["dist"], "polylines": polylines}


def get_pair(city: str, origin: dict, destination: dict) -> dict | None:
    """获取单对点驾车数据（方向敏感）。

    缓存命中直接返回；未命中调 _get_driving_data 拉取并写入缓存。

    Args:
        city: 所在城市。
        origin: 起点 {name, lon, lat}。
        destination: 终点 {name, lon, lat}。

    Returns:
        dict | None: {duration_min, distance_km, polyline?}；拉取失败（无耗时）返回 None。
    """
    cached = get_driving_pair(city, origin, destination)
    if cached is not None:
        return cached
    d_km, dur, poly = _get_driving_data(
        (origin["lon"], origin["lat"]), (destination["lon"], destination["lat"])
    )
    if dur is None or d_km is None:
        return None
    data: dict = {"duration_min": round(dur / 60.0, 2), "distance_km": round(d_km, 2)}
    if poly:
        data["polyline"] = poly
    set_driving_pair(city, origin, destination, data)
    return data


def get_polyline(origin: tuple[float, float], destination: tuple[float, float]) -> str | None:
    """获取单段驾车 polyline（补调缺失段用，坐标级裸拉，不落点对缓存）。

    Args:
        origin: (经纬度) 起点坐标。
        destination: (经纬度) 终点坐标。

    Returns:
        str | None: 高德 polyline 字符串；拉取失败/无轨迹返回 None。
    """
    _, _, poly = _get_driving_data(origin, destination)
    return poly
