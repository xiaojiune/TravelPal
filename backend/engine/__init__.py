"""路径规划引擎层：双求解器（CA / VNS）、聚类方法、适应度评估、搜索调度。"""
from backend.engine.ca import CA_DEFAULT_PARAMS, CASolver
from backend.engine.clustering import CLUSTER_METHODS, call_cluster, find_method_func
from backend.engine.fitness import analyze_solution
from backend.engine.search import ca_suggest, cluster_and_solve, solve_groups
from backend.engine.vns import VNS_DEFAULT_PARAMS, VNSSolver

__all__ = [
    'VNSSolver',
    'VNS_DEFAULT_PARAMS',
    'CASolver',
    'CA_DEFAULT_PARAMS',
    'analyze_solution',
    'CLUSTER_METHODS',
    'call_cluster',
    'find_method_func',
    'cluster_and_solve',
    'solve_groups',
    'ca_suggest',
]
