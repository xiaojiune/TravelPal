"""改天数调整：保持景点不变，用新 n_days 重新规划。

被 engine/pipeline.adjust_plan 分发调用（方案调整编排入口）。
"""

import numpy as np

from backend.engine.search import cluster_and_solve
from backend.typedefs import SpotDict


def adjust_plan_days(
    spots_dict: dict[int, SpotDict],
    cost_matrix: np.ndarray,
    dist_matrix: np.ndarray,
    new_n_days: int,
) -> dict:
    """调整方案天数，保持景点不变，用新 n_days 重新规划。

    Args:
        spots_dict: 景点字典（与 run_planning 格式一致）。
        cost_matrix: np.ndarray 成本矩阵。
        dist_matrix: np.ndarray 距离矩阵（仅接收，不参与求解，用于矩阵一致性维护）。
        new_n_days: 新的行程天数。

    Returns:
        dict: cluster_and_solve 返回的 result，含 "type": "solution"。
    """
    from backend.engine.pipeline import _rebuild_schedule

    spots = {k: v for k, v in spots_dict.items()}
    cost = np.array(cost_matrix) if not isinstance(cost_matrix, np.ndarray) else cost_matrix
    depot = 0

    result = cluster_and_solve(
        spots,
        depot,
        cost,
        mode="fast",
        n_days=new_n_days,
    )

    if result["type"] != "solution":
        return result

    solution = result["solution"]
    daily_schedules = _rebuild_schedule(solution["routes"], spots, cost)
    return {
        "solution": solution,
        "best_days": new_n_days,
        "best_m": result["best_m"],
        "daily_schedules": daily_schedules,
    }
