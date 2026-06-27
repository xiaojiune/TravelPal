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


def ca_suggest(spots, depot, dist_mat, min_days=None, max_days=None,
               early_stop_gain_threshold=None, stop_consecutive_worse=None,
               travel_speed=1.0, penalty_weight=100.0,
               early_wait_weight=0.1, late_return_weight=50.0):
    if min_days is None:
        min_days = CA_DEFAULT_PARAMS["min_clusters"]
    if max_days is None:
        max_days = CA_DEFAULT_PARAMS["max_clusters"]
    if early_stop_gain_threshold is None:
        early_stop_gain_threshold = CA_DEFAULT_PARAMS["early_stop_gain_threshold"]
    if stop_consecutive_worse is None:
        stop_consecutive_worse = CA_DEFAULT_PARAMS["stop_consecutive_worse"]

    n_spots = len(spots) - 1
    max_days = min(max_days, n_spots)

    raw_results = []

    for method_name, method_func in CLUSTER_METHODS:
        best_cost = float("inf")
        best_days = min_days
        worse_count = 0

        for n_days in range(min_days, max_days + 1):
            groups = call_cluster(method_func, spots, depot, n_days, dist_mat)
            res = solve_groups(
                groups, spots, dist_mat, "CA",
                travel_speed, penalty_weight,
                early_wait_weight, late_return_weight,
            )
            raw_results.append({
                "method": method_name,
                "n_days": n_days,
                "cost": res["total_cost"],
                "groups": groups,
            })
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

    deduped = _deduplicate(raw_results)
    deduped.sort(key=lambda x: x["cost"])
    top5 = deduped[:5]

    return {
        "type": "suggestion",
        "suggestions": [
            {
                "n_days": item["n_days"],
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
            "best_days": n_days,
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
