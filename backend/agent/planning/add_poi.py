"""添加景点调整：向方案添加新景点并重新求解（矩阵已由调用方展开）。

被 engine/pipeline.adjust_plan 分发调用（方案调整编排入口）。
"""

import numpy as np

from backend.engine.search import cluster_and_solve
from backend.typedefs import SpotDict


def add_poi_to_plan(
    spots_dict: dict[int, SpotDict],
    cost_matrix: np.ndarray,
    dist_matrix: np.ndarray,
    routes: list,
) -> dict:
    """向方案添加新景点并重新求解（矩阵已由调用方展开）。

    Args:
        spots_dict: 景点字典（含新 POI，矩阵已对应展开）。
        cost_matrix: 展开后的成本矩阵（ndarray）。
        dist_matrix: 展开后的距离矩阵（ndarray，仅接收，不参与求解）。
        routes: 当前方案的路径列表（仅用于获取天数）。

    Returns:
        dict: 与 adjust_plan_days 格式一致的新方案。
    """
    from backend.engine.pipeline import _rebuild_schedule

    n_days = len(routes)
    result = cluster_and_solve(spots_dict, 0, cost_matrix, mode="fast", n_days=n_days)
    if result["type"] != "solution":
        return result
    solution = result["solution"]
    daily_schedules = _rebuild_schedule(solution["routes"], spots_dict, cost_matrix)
    return {
        "solution": solution,
        "best_days": n_days,
        "best_m": "add_poi",
        "daily_schedules": daily_schedules,
    }
