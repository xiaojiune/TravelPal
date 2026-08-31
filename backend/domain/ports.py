"""领域端口（六边形/整洁架构）：domain 只定义端口（抽象），实现由基础设施层提供。

依赖方向：domain 零依赖纯接口；实现层（infrastructure / data / engine）实现本文件的端口，
这样换实现（多数据源、可插拔算法引擎）不动 domain。
"""

from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class DrivingDataProvider(Protocol):
    """数据获取端口：驾车矩阵/点对/polyline。

    OR 编排层（pipeline）只依赖本端口，不依赖具体实现；可注入不同数据源
    （高德 / 多 travel_mode / 多 API 键 / 后续 ML 偏好上下文）。
    """

    def get_matrix(self, city: str, poi_names: list, coords: list, cancel_check=None) -> dict: ...

    def get_pair(self, city: str, origin: dict, destination: dict) -> dict | None: ...

    def get_polyline(self, origin: tuple[float, float], destination: tuple[float, float]) -> str | None: ...


@runtime_checkable
class Solver(Protocol):
    """算法求解器端口：给定分组、景点、矩阵与软约束权重，返回最优解。

    CASolver/VNSSolver/未来统一 OR 引擎都实现本端口；编排层经 get_solver(name) 选实现，
    可插拔（换算法 = 换注入的求解器）。
    """

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


@runtime_checkable
class SessionStore(Protocol):
    """会话存储端口：服务端会话（登录态）的读写。

    定义在 domain；实现（Redis 等）在 infrastructure，供登录/鉴权接入层注入。
    """

    def create(self, user_id: str) -> str | None: ...

    def get(self, session_id: str | None) -> str | None: ...

    def revoke(self, session_id: str | None) -> None: ...
