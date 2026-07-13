"""双模式分发：CA 全参数搜索建议 + 指定天数求解。"""

import time
import numpy as np
from backend.engine.ca import CASolver, CA_DEFAULT_PARAMS
from backend.engine.vns import VNSSolver
from backend.engine.clustering import CLUSTER_METHODS, call_cluster
from backend.engine.fitness import analyze_solution
from backend.typedefs import SpotDict, RouteResult

# ================== 分组求解 ==================

def balance_groups(groups: list, spots: dict[int, SpotDict], depot: int = 0) -> list:
    """
    强制均衡分组，确保每天的总停留时间接近。

    将景点按停留时间贪心分配到当前负荷最小的天，
    尽可能让每天的停留时间均匀分布。

    Args:
        groups: 原始分组（不含 depot），每组为景点索引列表。
        spots: 景点字典，键为索引，值为含 stay 字段的属性。
        depot: depot 索引，默认 0。

    Returns:
        均衡后的分组列表，每组含首尾 depot。
    """
    all_spots = []
    for g in groups:
        for node in g:
            if node != depot and node not in all_spots:
                all_spots.append(node)

    k = len(groups)
    new_groups = [[] for _ in range(k)]
    day_loads = [0] * k

    for spot in all_spots:
        stay = spots[spot]["stay"]
        min_idx = min(range(k), key=lambda i: day_loads[i])
        new_groups[min_idx].append(spot)
        day_loads[min_idx] += stay

    balanced = [[depot] + core + [depot] for core in new_groups]
    final_loads = [sum(spots[n]["stay"] for n in g if n != depot) for g in balanced]
    print(f"  均衡后每日停留负荷: {final_loads}, 目标均值: {sum(final_loads)/k:.0f} min")
    return balanced


def solve_groups(groups: list, spots: dict[int, SpotDict], cost_mat: np.ndarray, solver_type: str = "CA",
                 travel_speed: float = 1.0, penalty_weight: float = 100.0,
                 early_wait_weight: float = 0.1, late_return_weight: float = 50.0,
                 use_real_time_matrix: bool = False) -> RouteResult:
    """
    对已分组的路径逐一求解。

    遍历各组，为每组创建对应类型的求解器并执行求解。
    最后汇总所有组的成本、距离、等待、迟到等指标。

    Args:
        groups: 分组列表，每组为景点索引列表。
        spots: 景点字典，键为索引，值为景点属性。
        cost_mat: 距离/成本矩阵。
        solver_type: "CA" 或 "VNS"。
        travel_speed: 行驶速度（标准数据集），默认 1.0。
        penalty_weight: 违规惩罚权重。
        early_wait_weight: 早到等待惩罚权重。
        late_return_weight: 晚归惩罚权重。
        use_real_time_matrix: 是否使用高德真实旅行时间矩阵。

    Returns:
        dict: 包含 routes（路径列表）、histories（收敛历史）、total_cost、total_dist、wait、late、valid（是否覆盖所有景点）。
    """
    total_cost, total_dist, total_wait, total_late = 0, 0, 0, 0
    routes, histories = [], []
    for g in groups:
        if not g:
            continue
        if solver_type == "VNS":
            solver = VNSSolver(
                g, spots,
                travel_speed=travel_speed,
                penalty_weight=penalty_weight,
                early_wait_weight=early_wait_weight,
                late_return_weight=late_return_weight,
                use_real_time_matrix=use_real_time_matrix,
            )
        else:
            solver = CASolver(
                g, spots,
                travel_speed=travel_speed,
                penalty_weight=penalty_weight,
                early_wait_weight=early_wait_weight,
                late_return_weight=late_return_weight,
                use_real_time_matrix=use_real_time_matrix,
            )
        res = solver.solve(cost_mat)
        routes.append(res["best_solution"])
        histories.append(res["convergence_history"])
        total_cost += res["best_cost"]
        total_dist += res["best_distance"]
        # 求解器内部以 cost 为主，不直接暴露 wait/late 明细，因此重新调用 analyze_solution 提取详细指标
        _, _, w, l, _ = analyze_solution(
            res["best_solution"], cost_mat, spots, travel_speed,
            early_wait_weight=early_wait_weight,
            penalty_weight=penalty_weight,
            late_return_weight=late_return_weight, depot=0,
            use_real_time_matrix=use_real_time_matrix,
        )
        total_wait += w
        total_late += l
    # 校验所有非 depot 景点是否都已被覆盖
    visited = set()
    for r in routes:
        for c in r:
            if c != 0:
                visited.add(c)
    valid = (visited == set(range(1, len(spots))))
    return {
        "routes": routes,
        "histories": histories,
        "total_cost": total_cost,
        "total_dist": total_dist,
        "wait": total_wait,
        "late": total_late,
        "valid": valid,
    }


def _deduplicate(results: list) -> list:
    """用 frozenset 对 results 按分组结构去重，保留顺序中首次出现的唯一解。"""
    seen = set()
    deduped = []
    for item in results:
        groups = item["groups"]
        key = frozenset(frozenset(g) for g in groups)
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped

# ================== CA 全参数搜索 ==================

def ca_suggest(spots: dict[int, SpotDict], depot: int, cost_mat: np.ndarray,
               min_days: int | None = None,
               early_stop_gain_threshold: float | None = None,
               stop_consecutive_worse: int | None = None,
               travel_speed: float = 1.0, penalty_weight: float = 100.0,
               early_wait_weight: float = 0.1, late_return_weight: float = 50.0,
               use_real_time_matrix: bool = False) -> dict:
    """
    全参数搜索，输出全部可行方案建议（去重后）。

    遍历 6 种聚类方法 × min_days 向上递增，使用 CA 快速求解各组，
    按成本排序去重后返回全部方案。支持增益阈值式早退。

    Args:
        spots: 景点字典。
        depot: depot 索引。
        cost_mat: 距离/成本矩阵。
        min_days: 最小天数（默认 n_spots//8+1）。
        early_stop_gain_threshold: 增益阈值百分比（默认 1.0%），低于此视为无效改善。
        stop_consecutive_worse: 连续无效改善次数上限（默认 3）。
        travel_speed: 行驶速度。
        penalty_weight: 违规惩罚权重。
        early_wait_weight: 早到等待惩罚权重。
        late_return_weight: 晚归惩罚权重。
        use_real_time_matrix: 是否使用高德真实旅行时间矩阵。

    Returns:
        dict: type="suggestion"，suggestions 为全部可行方案的列表（含 n_days、method、cost、routes 等）。
    """
    n_spots = len(spots) - 1
    if min_days is None:
        min_days = max(1, n_spots // 8 + 1)
    if early_stop_gain_threshold is None:
        early_stop_gain_threshold = CA_DEFAULT_PARAMS["early_stop_gain_threshold"]
    if stop_consecutive_worse is None:
        stop_consecutive_worse = CA_DEFAULT_PARAMS["stop_consecutive_worse"]

    raw_results = []
    algo_start = time.time()

    for method_name, method_func in CLUSTER_METHODS:
        best_cost = float("inf")
        best_days = min_days
        worse_count = 0

        for n_days in range(min_days, n_spots + 1):
            groups = call_cluster(method_func, spots, depot, n_days, cost_mat)
            res = solve_groups(
                groups, spots, cost_mat, "CA",
                travel_speed, penalty_weight,
                early_wait_weight, late_return_weight,
                use_real_time_matrix=use_real_time_matrix,
            )
            raw_results.append({
                "method": method_name,
                "n_days": n_days,
                "cost": res["total_cost"],
                "total_dist": res["total_dist"],
                "wait": res["wait"],
                "late": res["late"],
                "groups": groups,
                "routes": res["routes"],
            })
            # 增益阈值早退：改善不明显（< early_stop_gain_threshold%）或连续变差达到上限时停止该聚类方法的搜索
            if res["total_cost"] < best_cost:
                improvement = (best_cost - res["total_cost"]) / best_cost * 100
                best_cost = res["total_cost"]
                best_days = n_days
                if improvement < early_stop_gain_threshold:
                    worse_count += 1
                else:
                    worse_count = 0
            else:
                if n_days > best_days:
                    worse_count += 1

            if worse_count >= stop_consecutive_worse:
                break

    # 先按成本排序再去重：不同聚类方法可能产出相同分组，靠后的运行轮次因 CA 随机性成本可能更低，排序确保每组保留最优解
    raw_results.sort(key=lambda x: x["cost"])
    deduped = _deduplicate(raw_results)

    return {
        "type": "suggestion",
        "algo_time": round(time.time() - algo_start, 2),
        "suggestions": [
            {
                "n_days": len(item["routes"]),
                "method": item["method"],
                "cost": item["cost"],
                "total_dist": item["total_dist"],
                "wait": item["wait"],
                "late": item["late"],
                "routes": item["routes"],
            }
            for item in deduped
        ],
        "message": "请指定行程天数以获得最终方案",
    }

# ================== 双模式分发 ==================

def cluster_and_solve(spots: dict[int, SpotDict], depot: int, cost_mat: np.ndarray,
                      mode: str = "fast", n_days: int | None = None,
                      min_days: int | None = None,
                      travel_speed: float = 1.0, penalty_weight: float = 100.0,
                      early_wait_weight: float = 0.1, late_return_weight: float = 50.0,
                      use_real_time_matrix: bool = False) -> dict:
    """
    双阶段路由入口。

    - 指定 n_days：遍历 6 种聚类方法，对每组调用对应求解器（CA/VNS）求最优解。
    - 未指定 n_days + mode="fast"：回退到 ca_suggest() 输出建议。
    - 未指定 n_days + mode="deep"：报错（VNS 无自动分群能力）。

    Args:
        spots: 景点字典。
        depot: depot 索引。
        cost_mat: 距离/成本矩阵。
        mode: "fast"（CA，秒级）或 "deep"（VNS，分钟级）。
        n_days: 行程天数。deep 模式必填。
        min_days: 建议模式最小搜索天数（默认由引擎自动推断）。
        travel_speed: 行驶速度。
        penalty_weight: 违规惩罚权重。
        early_wait_weight: 早到等待惩罚权重。
        late_return_weight: 晚归惩罚权重。
        use_real_time_matrix: 是否使用高德真实旅行时间矩阵。

    Returns:
        dict: type="suggestion"（未指定天数时）或 type="solution"（已指定天数时）。

    Raises:
        ValueError: mode="deep" 且未指定 n_days 时。
    """
    if n_days is not None:
        solver_type = "VNS" if mode == "deep" else "CA"
        best_cost = float("inf")
        best_result = None
        best_m = None
        best_groups = None

        for method_name, method_func in CLUSTER_METHODS:
            groups = call_cluster(method_func, spots, depot, n_days, cost_mat)
            res = solve_groups(
                groups, spots, cost_mat, solver_type,
                travel_speed, penalty_weight,
                early_wait_weight, late_return_weight,
                use_real_time_matrix=use_real_time_matrix,
            )
            if res["total_cost"] < best_cost:
                best_cost = res["total_cost"]
                best_result = res
                best_m = method_name
                best_groups = groups

        return {
            "type": "solution",
            "solution": best_result,
            "best_days": n_days,
            "best_m": best_m,
        }

    if mode == "deep":
        raise ValueError("深度模式(VNS)需要指定 n_days，请先通过 ca_suggest() 获取建议")

    return ca_suggest(
        spots, depot, cost_mat,
        min_days=min_days,
        travel_speed=travel_speed,
        penalty_weight=penalty_weight,
        early_wait_weight=early_wait_weight,
        late_return_weight=late_return_weight,
        use_real_time_matrix=use_real_time_matrix,
    )
