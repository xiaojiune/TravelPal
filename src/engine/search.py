import numpy as np
from src.engine.ca import CASolver, CA_DEFAULT_PARAMS
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


def _deduplicate(results):
    seen = set()
    deduped = []
    for item in results:
        groups = item["groups"]
        key = frozenset(frozenset(g) for g in groups)
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped


def ca_suggest(spots, depot, dist_mat, min_clusters=None, max_clusters=None,
               stop_consecutive_worse=None, travel_speed=1.0,
               penalty_weight=100.0, early_wait_weight=0.1,
               late_return_weight=50.0):
    if min_clusters is None:
        min_clusters = CA_DEFAULT_PARAMS["min_clusters"]
    if max_clusters is None:
        max_clusters = CA_DEFAULT_PARAMS["max_clusters"]
    if stop_consecutive_worse is None:
        stop_consecutive_worse = CA_DEFAULT_PARAMS["stop_consecutive_worse"]

    n_spots = len(spots) - 1
    max_k = min(max_clusters, n_spots)

    raw_results = []

    for method_name, method_func in CLUSTER_METHODS:
        best_cost = float("inf")
        best_k = min_clusters
        worse_count = 0

        for k in range(min_clusters, max_k + 1):
            groups = call_cluster(method_func, spots, depot, k, dist_mat)
            res = solve_groups(
                groups, spots, dist_mat, "CA",
                travel_speed, penalty_weight,
                early_wait_weight, late_return_weight,
            )
            raw_results.append({
                "method": method_name,
                "k": k,
                "cost": res["total_cost"],
                "groups": groups,
            })
            if res["total_cost"] < best_cost:
                best_cost = res["total_cost"]
                best_k = k
                worse_count = 0
            else:
                if k > best_k:
                    worse_count += 1
                    if worse_count >= stop_consecutive_worse:
                        break

    deduped = _deduplicate(raw_results)
    deduped.sort(key=lambda x: x["cost"])
    top5 = deduped[:5]

    return {
        "type": "suggestion",
        "suggestions": [
            {
                "k": item["k"],
                "method": item["method"],
                "cost": item["cost"],
                "groups": item["groups"],
            }
            for item in top5
        ],
        "message": "请指定行程天数以获得最终方案",
    }


def cluster_and_solve(spots, depot, dist_mat, mode="fast",
                      n_days=None, travel_speed=1.0,
                      penalty_weight=100.0, early_wait_weight=0.1,
                      late_return_weight=50.0):
    if n_days is not None:
        solver_type = "VNS" if mode == "deep" else "CA"
        best_cost = float("inf")
        best_result = None
        best_m = None
        best_groups = None

        for method_name, method_func in CLUSTER_METHODS:
            groups = call_cluster(method_func, spots, depot, n_days, dist_mat)
            res = solve_groups(
                groups, spots, dist_mat, solver_type,
                travel_speed, penalty_weight,
                early_wait_weight, late_return_weight,
            )
            if res["total_cost"] < best_cost:
                best_cost = res["total_cost"]
                best_result = res
                best_m = method_name
                best_groups = groups

        return {
            "type": "solution",
            "solution": best_result,
            "best_k": n_days,
            "best_m": best_m,
        }

    if mode == "deep":
        raise ValueError("深度模式(VNS)需要指定 n_days，请先通过 ca_suggest() 获取建议")

    return ca_suggest(
        spots, depot, dist_mat,
        travel_speed=travel_speed,
        penalty_weight=penalty_weight,
        early_wait_weight=early_wait_weight,
        late_return_weight=late_return_weight,
    )
