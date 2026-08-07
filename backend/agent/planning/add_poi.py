"""添加景点调整：向方案添加新景点并重排（单日/全局两种模式）。

被 engine/pipeline.adjust_plan 分发调用（方案调整编排入口）。

- add_poi_to_day：单日重排（add_poi 工具主路径）——只对目标天重新求解，
  其余天路线原样保留，计算秒级、调整可预期。day 由编排层从对话明确提取。
- add_poi_to_plan：全局重排（@placeholder 未启用）——遍历 6 种聚类全量重分组，
  保留供未来「Agent 自判断 + CA 多解缓存」扩展，当前工具路径不触达。
"""

import numpy as np

from backend.engine.fitness import analyze_solution
from backend.engine.search import solve_groups
from backend.typedefs import SpotDict
from backend.utils.decorators import placeholder


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
    仅对目标天调用 solve_groups 求解，其余天路线原样保留。最后重组全部
    路线并重建每日行程，成本指标对各天重新分析汇总。

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
    from backend.engine.pipeline import _rebuild_schedule

    n_days = len(routes)
    if not 0 <= day < n_days:
        raise ValueError(f"目标天 day={day} 超出范围，方案共 {n_days} 天（第 1 天=0）")

    # 剥掉首尾 depot 取每天核心节点，新点加入目标天
    core_days = [r[1:-1] if len(r) > 2 and r[0] == 0 else r for r in routes]
    core_days[day] = list(core_days[day]) + [new_idx]

    # 只解目标天（CA），其余天路线原样保留
    day_result = solve_groups(
        [core_days[day]],
        spots_dict,
        cost_matrix,
        solver_type="CA",
    )
    new_routes = list(routes)
    new_routes[day] = day_result["routes"][0]

    # 对各天重新分析成本汇总（目标天用求解结果路线，其余天用原路线）
    total_cost = total_dist = total_wait = total_late = 0.0
    visited = set()
    for r in new_routes:
        for node in r:
            if node != 0:
                visited.add(node)
        total, dist, wait, late, _ = analyze_solution(r, cost_matrix, spots_dict)
        total_cost += total
        total_dist += dist
        total_wait += wait
        total_late += late

    valid = visited == set(range(1, len(spots_dict)))
    solution = {
        "routes": new_routes,
        "total_cost": round(total_cost, 1),
        "total_dist": round(total_dist, 1),
        "wait": round(total_wait, 1),
        "late": round(total_late, 1),
        "valid": valid,
    }
    daily_schedules = _rebuild_schedule(new_routes, spots_dict, cost_matrix)
    return {
        "solution": solution,
        "best_days": n_days,
        "best_m": "add_poi",
        "daily_schedules": daily_schedules,
    }


@placeholder
def add_poi_to_plan(
    spots_dict: dict[int, SpotDict],
    cost_matrix: np.ndarray,
    dist_matrix: np.ndarray,
    routes: list,
) -> dict:
    """向方案添加新景点并全局重新求解（@placeholder 未启用）。

    与 add_poi_to_day 不同：遍历 6 种聚类方法对全部景点重新分组求解，
    所有天的组合都可能变化。保留供未来「Agent 自判断 + CA 多解缓存」
    扩展，当前 add_poi 工具只走单日路径（add_poi_to_day），不触达本函数。

    Args:
        spots_dict: 景点字典（含新 POI，矩阵已对应展开）。
        cost_matrix: 展开后的成本矩阵（ndarray）。
        dist_matrix: 展开后的距离矩阵（ndarray，仅接收，不参与求解）。
        routes: 当前方案的路径列表（仅用于获取天数）。

    Returns:
        dict: 与 adjust_plan_days 格式一致的新方案。
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
