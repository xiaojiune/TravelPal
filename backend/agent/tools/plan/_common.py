"""方案调整工具共用逻辑：确保方案快照含驾车矩阵（快照缓存兜底）。

供 plan/add.py 与 plan/remove.py 复用。下划线前缀标记「包内私有公共模块」，
不进 __all__ / 不对外导出（对齐 planning/_core.py 先例）。
"""

from backend.data.driving_cache import get_driving_matrix


def ensure_matrix(plan: dict, city: str) -> bool:
    """确保方案快照含驾车矩阵；缺失时从矩阵快照缓存补全。

    fast 模式前端合成的 planResult 不含 cost_matrix/dist_matrix（阶段「矩阵快照
    缓存」改造后前端零矩阵），而 add_poi/remove_poi 重排依赖矩阵。此处从驾车
    矩阵快照缓存（键=city+点集合指纹）读取补全，命中即注入 plan。

    Args:
        plan: 方案快照（PlanResult dict，可能缺 cost_matrix/dist_matrix）。
        city: 所在城市（矩阵快照键前缀）。

    Returns:
        bool: 补全后 plan 是否含完整矩阵（spots/solution 已存在的前提下）。
    """
    if plan.get("cost_matrix") and plan.get("dist_matrix"):
        return True
    spots = plan.get("spots")
    if not spots:
        return False
    try:
        # spots 键为 str（JSON 反序列化后）或 int，统一按索引排序取点
        names: list[str] = []
        coords: list[tuple[float, float]] = []
        for idx in sorted(spots, key=lambda k: int(k)):
            s = spots[idx]
            names.append(s["name"])
            coords.append((float(s["x"]), float(s["y"])))
        snapshot = get_driving_matrix(city, names, coords)
        if snapshot is None:
            return False
        plan["cost_matrix"] = snapshot["cost"]
        plan["dist_matrix"] = snapshot["dist"]
        return True
    except Exception:
        return False
