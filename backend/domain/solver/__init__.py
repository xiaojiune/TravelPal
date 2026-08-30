"""OR 求解子域：聚类 + 目标函数 + 分组求解（纯算法，零 IO）。

从 domain/ 平铺结构归位为独立子域，收敛聚类、适应度、求解入口。
该子域只暴露求解相关公共接口，具体实现见 infrastructure/engine/。

公开符号：
- solve_groups / ca_suggest / cluster_and_solve：分组求解入口（search.py）
- analyze_solution：行程分析（fitness.py）
- CLUSTER_METHODS / call_cluster：聚类方法注册 + 分发（clustering.py）

内部实现（_cal_fitness_numba 等私有符号）不在此导出，如需请直接 import 子模块。
"""

from backend.domain.solver.clustering import CLUSTER_METHODS, call_cluster
from backend.domain.solver.fitness import analyze_solution
from backend.domain.solver.search import ca_suggest, cluster_and_solve, solve_groups

__all__ = [
    "CLUSTER_METHODS",
    "call_cluster",
    "analyze_solution",
    "ca_suggest",
    "cluster_and_solve",
    "solve_groups",
]
