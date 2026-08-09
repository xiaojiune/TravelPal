"""添加景点调整：向方案添加新景点并重排（单日/全局两种模式）。

被 engine/pipeline.adjust_plan 分发调用（方案调整编排入口）。

- add_poi_to_day：单日重排——只对目标天重新求解，其余天路线原样保留。
  day 由编排层从对话明确提取。
- add_poi_to_plan：全局重排——遍历 6 种聚类全量重分组。
  day 缺失（用户意图未定）时由 pipeline 兜底调用（与 remove_poi_from_plan 对称）。
"""

import numpy as np

from backend.agent.planning._core import extract_cores, reorder_from_cores
from backend.typedefs import SpotDict


def add_poi_to_day(
    spots_dict: dict[int, SpotDict],
    cost_matrix: np.ndarray,
    dist_matrix: np.ndarray,
    routes: list,
    new_idx: int,
    day: int,
) -> dict:
    """向方案添加新景点并只对目标天重新求解（单日重排）。

    从 routes 提取每天核心节点（剥掉首尾 depot），把新点加入目标天，
    仅对目标天调用求解器，其余天路线原样保留。最终重组全部路线并重建
    每日行程，成本指标对各天重新分析汇总。

    Args:
        spots_dict: 景点字典（含新 POI，矩阵已对应展开）。
        cost_matrix: 展开后的成本矩阵（ndarray）。
        dist_matrix: 展开后的距离矩阵（ndarray，仅接收，不参与求解）。
        routes: 当前方案的路径列表（每组含首尾 depot）。
        new_idx: 新点在 spots_dict 中的索引。
        day: 目标天索引（0-indexed，第 1 天 = 0）。

    Returns:
        dict: { solution, best_days, best_m, daily_schedules }，
            solution 含 routes/total_cost/total_dist/wait/late/valid。

    Raises:
        ValueError: day 超出 [0, len(routes)) 范围。
    """
    cores = extract_cores(routes)
    n_days = len(routes)
    if not 0 <= day < n_days:
        raise ValueError(f"目标天 day={day} 超出范围，方案共 {n_days} 天（第 1 天=0）")
    cores[day] = list(cores[day]) + [new_idx]
    plan = reorder_from_cores(spots_dict, cost_matrix, routes, cores, only_day=day)
    plan["best_m"] = "add_poi"
    return plan


def add_poi_to_plan(
    spots_dict: dict[int, SpotDict],
    cost_matrix: np.ndarray,
    dist_matrix: np.ndarray,
    routes: list,
) -> dict:
    """向方案添加新景点并全局重新求解。

    与 add_poi_to_day 不同：遍历 6 种聚类方法对全部景点重新分组求解，
    所有天的组合都可能变化。day 缺失（用户意图未定）时由 pipeline
    adjust_plan 兜底调用。

    Args:
        spots_dict: 景点字典（含新 POI，矩阵已对应展开）。
        cost_matrix: 展开后的成本矩阵（ndarray）。
        dist_matrix: 展开后的距离矩阵（ndarray，仅接收，不参与求解）。
        routes: 当前方案的路径列表（仅用于获取天数）。

    Returns:
        dict: 重排后的完整方案（solution/best_days/best_m/daily_schedules）。
    """
    from backend.engine.pipeline import _rebuild_schedule
    from backend.engine.search import cluster_and_solve

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
