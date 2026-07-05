# ================== 接口清单 ==================
#
# ---- vns.py ----
# VNSSolver(city_indices, spots_dict, travel_speed=1.0, ..., depot_index=0) -> 求解器实例  变邻域搜索，VND + 自适应权重 + 精英池
#   solver.solve(dis_matrix, initial_solution=None) -> dict                                  VNS 主循环入口
#   solver.get_elite_pool() -> List                                                           返回精英池
# VNS_DEFAULT_PARAMS -> 默认参数字典                                                           含 max_iter、SA 退火、精英池等参数
#
# ---- ca.py ----
# CASolver(city_indices, spots_dict, ...) -> 求解器实例                   压缩退火，动态调节距离/惩罚权重
#   solver.solve(dis_matrix) -> dict                                       CA 主循环入口
#   CA_DEFAULT_PARAMS -> 默认参数字典                                      含压缩系数、退火参数、早退阈值等
#
# ---- fitness.py ----
# analyze_solution(solution, dis_matrix, spots_dict, travel_speed, ...) -> Tuple  解析路径的详细成本与违规信息
#
# ---- clustering.py ----
# CLUSTER_METHODS -> List[Tuple[str, callable]]                           6 种聚类方法注册表
# call_cluster(func, spots, depot, k, dist_mat=None) -> List[List[int]]   统一调用聚类方法
# find_method_func(name) -> callable | None                               按名称查找聚类函数
#
# ---- search.py ----
# cluster_and_solve(spots, depot, dist_mat, mode="fast", n_days=None, use_real_time_matrix=False, ...) -> dict  双阶段路由入口
# solve_groups(groups, spots, dist_mat, solver_type="CA", use_real_time_matrix=False, ...) -> dict              对已分组路径逐一求解
# ca_suggest(spots, depot, dist_mat, min_days=None, max_days=None, use_real_time_matrix=False, ...) -> dict     全参数搜索，输出 top-5 建议

from backend.engine.vns import VNSSolver, VNS_DEFAULT_PARAMS
from backend.engine.ca import CASolver, CA_DEFAULT_PARAMS
from backend.engine.fitness import analyze_solution
from backend.engine.clustering import CLUSTER_METHODS, call_cluster, find_method_func
from backend.engine.search import cluster_and_solve, solve_groups, ca_suggest

__all__ = [
    'VNSSolver', 'VNS_DEFAULT_PARAMS',
    'CASolver', 'CA_DEFAULT_PARAMS',
    'analyze_solution',
    'CLUSTER_METHODS', 'call_cluster', 'find_method_func',
    'cluster_and_solve', 'solve_groups', 'ca_suggest',
]
