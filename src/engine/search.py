import numpy as np
from src.engine.sa import SASolver
from src.engine.vns import VNSSolver
from src.engine.clustering import CLUSTER_METHODS, call_cluster
from src.engine.fitness import analyze_solution


def solve_groups(groups, spots, dist_mat, travel_speed=1.0,
                 penalty_weight=100.0, early_wait_weight=0.1, late_return_weight=50.0):
    total_cost, total_dist, total_wait, total_late = 0, 0, 0, 0
    routes, histories = [], []
    for g in groups:
        if not g:
            continue
        solver = SASolver(
            g, spots,
            travel_speed=travel_speed,
            penalty_weight=penalty_weight,
            early_wait_weight=early_wait_weight,
            late_return_weight=late_return_weight
        )
        res = solver.solve(dist_mat)
        routes.append(res['best_solution'])
        histories.append(res['convergence_history'])
        total_cost += res['best_cost']
        total_dist += res['best_distance']
        _, _, w, l, _ = analyze_solution(
            res['best_solution'], dist_mat, spots, travel_speed,
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
        'routes': routes,
        'histories': histories,
        'total_cost': total_cost,
        'total_dist': total_dist,
        'wait': total_wait,
        'late': total_late,
        'valid': valid
    }


def sa_vns_pipeline(spots, depot, dist_mat, travel_speed=1.0,
                    penalty_weight=100.0, early_wait_weight=0.1,
                    late_return_weight=50.0, min_clusters=1, max_clusters=10):
    print(">>> SA 阶段：搜索最优分组数与聚类方法...")

    best_k = min_clusters
    best_m = None
    best_cost = float('inf')
    best_groups = None

    for full_name, method_func in CLUSTER_METHODS:
        for k in range(min_clusters, min(max_clusters, len(spots) - 1) + 1):
            groups = call_cluster(method_func, spots, depot, k, dist_mat)
            res = solve_groups(groups, spots, dist_mat, travel_speed,
                               penalty_weight, early_wait_weight, late_return_weight)
            if res['total_cost'] < best_cost:
                best_cost = res['total_cost']
                best_k = k
                best_m = full_name
                best_groups = groups

    print(f"  SA 最优: k={best_k}, m={best_m}, cost={best_cost:.1f}")

    sa_res = solve_groups(best_groups, spots, dist_mat, travel_speed,
                          penalty_weight, early_wait_weight, late_return_weight)

    print(">>> VNS 阶段：精炼每日路线...")
    refined_routes = []
    refined_histories = []
    vns_total_cost = 0
    vns_total_dist = 0
    vns_total_wait = 0
    vns_total_late = 0

    for day_idx, route in enumerate(sa_res['routes']):
        day_cities = [c for c in route if c != depot]
        if not day_cities:
            refined_routes.append(route)
            continue
        vns = VNSSolver(
            day_cities, spots,
            travel_speed=travel_speed,
            penalty_weight=penalty_weight,
            early_wait_weight=early_wait_weight,
            late_return_weight=late_return_weight,
            depot_index=depot
        )
        vns_res = vns.solve(dist_mat, initial_solution=route)
        refined_routes.append(vns_res['best_solution'])
        refined_histories.append(vns_res['convergence_history'])
        vns_total_cost += vns_res['best_cost']
        vns_total_dist += vns_res['best_distance']
        _, _, w, l, _ = analyze_solution(
            vns_res['best_solution'], dist_mat, spots, travel_speed,
            early_wait_weight, penalty_weight, late_return_weight, depot
        )
        vns_total_wait += w
        vns_total_late += l

    visited = set()
    for r in refined_routes:
        for c in r:
            if c != 0:
                visited.add(c)
    valid = (visited == set(range(1, len(spots))))

    vns_res = {
        'routes': refined_routes,
        'histories': refined_histories,
        'total_cost': vns_total_cost,
        'total_dist': vns_total_dist,
        'wait': vns_total_wait,
        'late': vns_total_late,
        'valid': valid
    }

    improvement = ((sa_res['total_cost'] - vns_res['total_cost']) / sa_res['total_cost'] * 100
                   if sa_res['total_cost'] > 0 else 0)
    print(f"  SA 总成本: {sa_res['total_cost']:.1f}")
    print(f"  VNS 总成本: {vns_res['total_cost']:.1f}")
    print(f"  提升: {improvement:.1f}%")

    return {
        'sa_result': sa_res,
        'vns_result': vns_res,
        'best_k': best_k,
        'best_m': best_m,
        'improvement': improvement
    }
