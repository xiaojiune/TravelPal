"""移除景点调整：从方案移除指定景点并重新求解（单日/全局两种模式）。

被 engine/pipeline.adjust_plan 分发调用（方案调整编排入口）。

- remove_poi_from_day：单日重排——只对目标天重新求解，其余天路线原样
  保留。删除导致目标天空时废弃该天（best_days 减 1）并发出警告。
- remove_poi_from_plan：全局重排——保持分组结构对全部天做组内重排。
  day 缺失（用户意图未定）时由 pipeline 兜底调用（与 add_poi_to_plan 对称）。
"""

import warnings

import numpy as np

from backend.agent.planning._core import extract_cores, reorder_from_cores
from backend.typedefs import SpotDict

__all__ = ["remove_poi_from_day", "remove_poi_from_plan"]


def _locate_and_remove(
    spots_dict: dict[int, SpotDict],
    cost_matrix: np.ndarray,
    dist_matrix: np.ndarray,
    routes: list,
    poi_name: str,
) -> tuple[dict[int, SpotDict], np.ndarray, np.ndarray, list, int, int]:
    """定位景点、删除行列、重映射索引，返回整理后的结构。

    Args:
        spots_dict: 景点字典。
        cost_matrix: 成本矩阵（ndarray）。
        dist_matrix: 距离矩阵（ndarray）。
        routes: 当前方案的路径列表（每组含首尾 depot）。
        poi_name: 要移除的景点名称。

    Returns:
        (spots, cost, dist, routes, removed_idx, n_days):
            spots 为删除并重映射后的新字典（0 起连续索引）；
            cost/dist 为对应删行删列后的矩阵；
            routes 为删除并重映射后的路径；
            removed_idx 为被删景点的旧索引；n_days 为原天数。

    Raises:
        ValueError: 未找到景点，或目标为酒店（索引 0，不可删除）。
    """
    idx_to_remove = None
    for idx, spot in spots_dict.items():
        if spot["name"] == poi_name and idx != 0:
            idx_to_remove = idx
            break
    if idx_to_remove is None:
        if any(spots_dict.get(0, {}).get("name") == poi_name for _ in [0]):
            raise ValueError(f"不能删除酒店（depot）：{poi_name}")
        raise ValueError(f"未找到景点: {poi_name}")

    spots = dict(spots_dict)
    spots.pop(idx_to_remove)
    cost = np.delete(np.delete(cost_matrix, idx_to_remove, axis=0), idx_to_remove, axis=1)
    dist = np.delete(np.delete(dist_matrix, idx_to_remove, axis=0), idx_to_remove, axis=1)

    mapping: dict[int, int] = {}
    new_spots: dict[int, SpotDict] = {}
    new_idx = 0
    for old_idx in sorted(spots.keys()):
        mapping[old_idx] = new_idx
        new_spots[new_idx] = spots[old_idx]
        new_idx += 1

    new_routes = []
    for route in routes:
        new_route = [mapping.get(n, n) if n != idx_to_remove else None for n in route]
        new_route = [n for n in new_route if n is not None]
        if len(new_route) > 1:
            new_routes.append(new_route)

    return new_spots, cost, dist, new_routes, idx_to_remove, len(routes)


def remove_poi_from_day(
    spots_dict: dict[int, SpotDict],
    cost_matrix: np.ndarray,
    dist_matrix: np.ndarray,
    routes: list,
    poi_name: str,
    day: int,
) -> dict:
    """从指定天移除景点并只对该天重新求解（单日重排）。

    删除后该天空（无任何景点）时废弃该天：best_days 减 1，并发出
    UserWarning 提示。其余天路线原样保留。

    Args:
        spots_dict: 景点字典。
        cost_matrix: np.ndarray 成本矩阵。
        dist_matrix: np.ndarray 距离矩阵（仅接收，用于矩阵一致性维护）。
        routes: 当前方案的路径列表。
        poi_name: 要移除的景点名称。
        day: 目标天索引（0-indexed，第 1 天 = 0）。

    Returns:
        dict: { solution, best_days, best_m, daily_schedules }。

    Raises:
        ValueError: 未找到景点 / 目标为酒店 / day 越界。
    """
    spots, cost, dist, new_routes, _, n_days = _locate_and_remove(
        spots_dict, cost_matrix, dist_matrix, routes, poi_name
    )
    if day < 0 or day >= len(new_routes):
        raise ValueError(f"目标天 day={day} 超出范围，方案共 {len(new_routes)} 天（第 1 天=0）")

    cores = extract_cores(new_routes)
    core = [n for n in cores[day] if n != -1]

    # 删除后目标天空 → 废弃该天
    if not core:
        warnings.warn(
            f"景点 '{poi_name}' 删除后，第 {day + 1} 天已无任何景点，该天已废弃（总天数 -1）",
            UserWarning,
            stacklevel=2,
        )
        remaining = [c for i, c in enumerate(cores) if i != day]
        plan = reorder_from_cores(spots, cost, new_routes[:day] + new_routes[day + 1 :], remaining, only_day=None)
        plan["best_m"] = "remove_poi"
        return plan

    cores[day] = core
    plan = reorder_from_cores(spots, cost, new_routes, cores, only_day=day)
    plan["best_m"] = "remove_poi"
    return plan


def remove_poi_from_plan(
    spots_dict: dict[int, SpotDict],
    cost_matrix: np.ndarray,
    dist_matrix: np.ndarray,
    routes: list,
    poi_name: str,
) -> dict:
    """从方案移除景点并保持分组全方案重排。

    删除景点并重映射后，对全部天做组内重排（组结构不变）。day 缺失
    （用户意图未定）时由 pipeline adjust_plan 兜底调用。

    Args:
        spots_dict: 景点字典。
        cost_matrix: np.ndarray 成本矩阵。
        dist_matrix: np.ndarray 距离矩阵（仅接收，用于矩阵一致性维护）。
        routes: 当前方案的路径列表。
        poi_name: 要移除的景点名称。

    Returns:
        dict: 重排后的完整方案（solution/best_days/best_m/daily_schedules）。

    Raises:
        ValueError: 未找到景点 / 目标为酒店。
    """
    spots, cost, dist, new_routes, _, _ = _locate_and_remove(spots_dict, cost_matrix, dist_matrix, routes, poi_name)
    cores = extract_cores(new_routes)
    plan = reorder_from_cores(spots, cost, new_routes, cores, only_day=None)
    plan["best_m"] = "remove_poi"
    return plan
