"""方案重排公共内核：extract_cores + reorder_from_cores。

add/remove 方案调整共享的核心抽象——把「增/删景点」统一为「对每日 core
节点集合的修改」，本模块只负责「给定每日核心节点 → 重排 → 汇总成本 → 重建行程」。

两个粒度由一个参数区分：
- only_day=day：单日组内重排（只解目标天，其余天路线原样保留）
- only_day=None：保持分组全方案重排（各组组内求解，天组结构不变）

注意：本模块不做「重新聚类分组」（那是 add_poi_to_plan 用 cluster_and_solve
的语义），只做组内重排。重新分组语义不在此抽象内。
"""

import numpy as np

from backend.engine.fitness import analyze_solution
from backend.engine.search import solve_groups
from backend.typedefs import SpotDict

__all__ = ["extract_cores", "reorder_from_cores"]


def extract_cores(routes: list) -> list[list[int]]:
    """剥掉每组首尾 depot，取每天的核心景点节点。

    Args:
        routes: 方案路径列表，每组含首尾 depot（如 [0, 3, 1, 0]）。

    Returns:
        list[list[int]]: 每天的核心节点列表（不含 depot）。
        首节点非 0 的路线原样返回（视为无 depot 结构）；
        短于 3 的路线剥掉两端 0 后可能为空（退化空天）。
    """
    cores = []
    for r in routes:
        if r and r[0] == 0 and len(r) >= 3:
            cores.append([n for n in r[1:-1] if n != 0])
        elif r and r[0] == 0:
            cores.append([n for n in r if n != 0])
        else:
            cores.append(list(r))
    return cores


def reorder_from_cores(
    spots_dict: dict[int, SpotDict],
    cost_matrix: np.ndarray,
    routes: list,
    cores: list[list[int]],
    only_day: int | None = None,
) -> dict:
    """给定每日核心节点集合，重排并生成新方案。

    Args:
        spots_dict: 景点字典（已含新增点 / 已删旧点，矩阵索引与其对齐）。
        cost_matrix: 成本矩阵（ndarray，与 spots_dict 对齐）。
        routes: 当前方案路径列表（每组含首尾 depot，用于确定天数结构）。
        cores: 修改后的每日核心节点集合（长度必须等于 routes 的天数）。
        only_day: 目标天索引（0-indexed）。为 None 时对全部天做组内重排；
            有值时只解该天，其余天路线原样保留。

    Returns:
        dict: { solution, best_days, best_m, daily_schedules }，
            solution 含 routes/total_cost/total_dist/wait/late/valid。

    Raises:
        ValueError: only_day 越界，或 cores 天数与 routes 不一致。
    """
    from backend.engine.pipeline import _rebuild_schedule

    n_days = len(routes)
    if len(cores) != n_days:
        raise ValueError(f"cores 天数 {len(cores)} 与方案天数 {n_days} 不一致")
    if only_day is not None and not 0 <= only_day < n_days:
        raise ValueError(f"目标天 day={only_day} 超出范围，方案共 {n_days} 天（第 1 天=0）")

    # 目标天集合（仅 only_day 指定时覆盖该天；否则全量）
    if only_day is None:
        target_cores = cores
    else:
        target_cores = [cores[only_day]]

    # 只解目标天（CA），其余天路线保留
    day_result = solve_groups(target_cores, spots_dict, cost_matrix, solver_type="CA")

    if only_day is None:
        new_routes = day_result["routes"]
    else:
        new_routes = list(routes)
        new_routes[only_day] = day_result["routes"][0]

    # 对各天重新分析成本汇总（逐条路线 analyze_solution）
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
        "best_m": "reorder",
        "daily_schedules": daily_schedules,
    }
