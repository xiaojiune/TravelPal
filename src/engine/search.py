import numpy as np
from src.engine.ca import CASolver
from src.engine.vns import VNSSolver
from src.engine.clustering import CLUSTER_METHODS, call_cluster
from src.engine.fitness import analyze_solution


def solve_groups(groups, spots, dist_mat, solver_type="CA",
                 travel_speed=1.0, penalty_weight=100.0,
                 early_wait_weight=0.1, late_return_weight=50.0):
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
            )
        else:
            solver = CASolver(
                g, spots,
                travel_speed=travel_speed,
                penalty_weight=penalty_weight,
                early_wait_weight=early_wait_weight,
                late_return_weight=late_return_weight,
            )
        res = solver.solve(dist_mat)
        routes.append(res["best_solution"])
        histories.append(res["convergence_history"])
        total_cost += res["best_cost"]
        total_dist += res["best_distance"]
        _, _, w, l, _ = analyze_solution(
            res["best_solution"], dist_mat, spots, travel_speed,
            early_wait_weight=early_wait_weight,
            penalty_weight=penalty_weight,
            late_return_weight=late_return_weight, depot=0
        )
        total_wait += w
        total_late += l
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


def cluster_and_solve(spots, depot, dist_mat, mode="fast",
                      n_days=None, min_clusters=None, max_clusters=None,
                      travel_speed=1.0, penalty_weight=100.0,
                      early_wait_weight=0.1, late_return_weight=50.0,
                      cluster_method_index=0):
    n_spots = len(spots) - 1

    if n_days is not None:
        k_range = [n_days]
    else:
        if min_clusters is None:
            min_clusters = max(1, n_spots // 25)
        if max_clusters is None:
            max_clusters = max(min_clusters + 1, min(n_spots // 5, 10))
        k_range = range(min_clusters, min(max_clusters, len(spots)) + 1)

    method_name, method_func = CLUSTER_METHODS[cluster_method_index]
    solver_type = "VNS" if mode == "deep" else "CA"

    best_cost = float("inf")
    best_result = None
    best_k = None
    best_groups = None

    print(f">>> 使用 {solver_type} 求解，搜索 k ∈ [{k_range[0]}, {k_range[-1]}]...")

    for k in k_range:
        groups = call_cluster(method_func, spots, depot, k, dist_mat)
        result = solve_groups(
            groups, spots, dist_mat, solver_type,
            travel_speed, penalty_weight,
            early_wait_weight, late_return_weight,
        )
        if result["total_cost"] < best_cost:
            best_cost = result["total_cost"]
            best_result = result
            best_k = k
            best_groups = groups

    print(f"  最优: k={best_k}, cost={best_cost:.1f}")

    return {
        "solution": best_result,
        "best_k": best_k,
        "best_m": method_name,
    }
