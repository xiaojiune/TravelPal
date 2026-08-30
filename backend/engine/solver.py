"""算法求解器端口：可插拔的 OR 引擎求解器抽象。

定义 Solver 端口（solve）+ 求解器注册表。编排层（cluster_and_solve / solve_groups）
经 get_solver(name) 取实现，不再硬编码 if solver_type 分支。
未来新算法（如统一 OR 引擎）注册进 SOLVER_REGISTRY 即可，编排层零改动。

依赖方向：编排层（engine/solver）→ 具体求解器实现（engine/ca、engine/vns）。
"""

from typing import Protocol, runtime_checkable

import numpy as np

from backend.engine.ca import CASolver
from backend.engine.vns import VNSSolver


@runtime_checkable
class Solver(Protocol):
    """可插拔求解器端口：给定分组、景点、矩阵与软约束权重，返回最优解。"""

    def __init__(
        self,
        city_indices: list[int],
        spots_dict: dict,
        *,
        penalty_weight: float = 100.0,
        early_wait_weight: float = 0.1,
        late_return_weight: float = 50.0,
        depot_index: int = 0,
        **kwargs,
    ) -> None: ...

    def solve(self, cost_mat: np.ndarray, initial_solution: list[int] | None = None) -> dict: ...


# 求解器注册表：名称 → 求解器类。CA/VNS 已注册，未来统一 OR 引擎在此新增。
SOLVER_REGISTRY: dict[str, type] = {
    "CA": CASolver,
    "VNS": VNSSolver,
}


def get_solver(name: str) -> type:
    """按名称取求解器类（端口-适配器：编排层经此选实现，避免硬编码分支）。

    Args:
        name: 求解器名，"CA" 或 "VNS"（未来可追加统一 OR 引擎等）。

    Returns:
        type: 求解器类。

    Raises:
        ValueError: 未注册的求解器名。
    """
    if name not in SOLVER_REGISTRY:
        raise ValueError(f"未知求解器: {name}（可用: {list(SOLVER_REGISTRY)}）")
    return SOLVER_REGISTRY[name]
