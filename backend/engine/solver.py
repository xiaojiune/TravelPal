"""求解器注册表：可插拔的 OR 引擎求解器。

Solver 端口（接口）定义在 domain/ports.py；本模块只保留"名称 → 求解器类"的注册，
编排层经 get_solver(name) 取实现。未来统一 OR 引擎在此注册即可，编排/调度零改动。
"""

from backend.engine.ca import CASolver
from backend.engine.vns import VNSSolver

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
