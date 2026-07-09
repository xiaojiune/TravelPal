import numpy as np
from backend.engine.search import cluster_and_solve, solve_groups
from backend.typedefs import SpotDict, RouteResult


def adjust_plan_days(spots_dict: dict[int, SpotDict], cost_matrix: np.ndarray, dist_matrix: np.ndarray, new_n_days: int) -> dict:
    """调整方案天数，保持景点不变，用新 n_days 重新规划。

    Args:
        spots_dict: 景点字典（与 run_planning 格式一致）。
        cost_matrix: np.ndarray 成本矩阵。
        dist_matrix: np.ndarray 距离矩阵。
        new_n_days: 新的行程天数。

    Returns:
        dict: cluster_and_solve 返回的 result，含 "type": "solution"。
    """
    from backend.engine.pipeline import _rebuild_schedule

    spots = {k: v for k, v in spots_dict.items()}
    cost = np.array(cost_matrix) if not isinstance(cost_matrix, np.ndarray) else cost_matrix
    dist = np.array(dist_matrix) if not isinstance(dist_matrix, np.ndarray) else dist_matrix
    depot = 0

    result = cluster_and_solve(
        spots, depot, cost, mode="fast",
        n_days=new_n_days,
    )

    if result["type"] != "solution":
        return result

    solution = result["solution"]
    daily_schedules = _rebuild_schedule(solution["routes"], spots, dist)
    return {
        "solution": solution,
        "best_days": new_n_days,
        "best_m": result["best_m"],
    "daily_schedules": daily_schedules,
}


# ================== 添加景点 ==================


def add_poi_to_plan(spots_dict: dict[int, SpotDict], cost_matrix: np.ndarray, dist_matrix: np.ndarray, routes: list) -> dict:
    """向方案添加新景点并重新求解（矩阵已由调用方展开）。

    Args:
        spots_dict: 景点字典（含新 POI，矩阵已对应展开）。
        cost_matrix: 展开后的成本矩阵（ndarray）。
        dist_matrix: 展开后的距离矩阵（ndarray）。
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
    daily_schedules = _rebuild_schedule(solution["routes"], spots_dict, dist_matrix)
    return {
        "solution": solution,
        "best_days": n_days,
        "best_m": "add_poi",
        "daily_schedules": daily_schedules,
    }


# ================== 移除景点 ==================


def remove_poi_from_plan(spots_dict: dict[int, SpotDict], cost_matrix: np.ndarray, dist_matrix: np.ndarray, routes: list, poi_name: str) -> dict:
    """从方案中移除指定景点并重新求解。

    Args:
        spots_dict: 景点字典。
        cost_matrix: np.ndarray 成本矩阵。
        dist_matrix: np.ndarray 距离矩阵。
        routes: 当前方案的路径列表。
        poi_name: 要移除的景点名称。

    Returns:
        dict: 与 adjust_plan_days 格式一致的新方案。

    Raises:
        ValueError: 未在 spots 中找到名称为 poi_name 的景点。
    """
    from backend.engine.pipeline import _rebuild_schedule

    cost = np.array(cost_matrix) if not isinstance(cost_matrix, np.ndarray) else cost_matrix
    dist = np.array(dist_matrix) if not isinstance(dist_matrix, np.ndarray) else dist_matrix
    spots = dict(spots_dict)

    idx_to_remove = None
    for idx, spot in spots.items():
        if spot["name"] == poi_name and idx != 0:
            idx_to_remove = idx
            break
    if idx_to_remove is None:
        raise ValueError(f"未找到景点: {poi_name}")

    spots.pop(idx_to_remove)
    cost = np.delete(np.delete(cost, idx_to_remove, axis=0), idx_to_remove, axis=1)
    dist = np.delete(np.delete(dist, idx_to_remove, axis=0), idx_to_remove, axis=1)

    mapping = {}
    new_spots = {}
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

    if not new_routes:
        new_n_days = 1
        result = cluster_and_solve(new_spots, 0, cost, mode="fast", n_days=new_n_days)
        if result["type"] != "solution":
            return result
        solution = result["solution"]
        daily_schedules = _rebuild_schedule(solution["routes"], new_spots, dist)
        return {
            "solution": solution,
            "best_days": new_n_days,
            "best_m": result["best_m"],
            "daily_schedules": daily_schedules,
        }

    groups = [r[1:-1] if len(r) > 2 and r[0] == 0 else r for r in new_routes]
    result = solve_groups(groups, new_spots, cost, solver_type="CA")
    routes = result["routes"]
    daily_schedules = _rebuild_schedule(routes, new_spots, dist)

    return {
        "solution": result,
        "best_days": len(routes),
        "best_m": "remove_poi",
        "daily_schedules": daily_schedules,
    }
