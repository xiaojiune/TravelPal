"""领域端口（六边形/整洁架构）：domain 只定义端口（抽象），实现由基础设施层提供。

依赖方向：domain 零依赖纯接口；实现层（infrastructure / data / engine）实现本文件的端口，
这样换实现（多数据源、可插拔算法引擎）不动 domain。
"""

from typing import Protocol, runtime_checkable
from uuid import UUID

import numpy as np

from backend.domain.conversation_rules import Conversation


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


class ConversationSession(Protocol):
    """会话存储端口：抽象会话表的域操作集（domain 不碰 sqlalchemy）。

    infra 提供一个 Adapter，由 ``AsyncSession`` 实现本协议（把 ORM 存取
    映射到 ``Conversation``）。domain 端只调用这些域级方法。
    """

    async def get(self, conversation_id: UUID) -> Conversation | None: ...

    async def find_recent(self, user_id: UUID | None) -> Conversation | None: ...

    def add(self, conversation: Conversation) -> None: ...

    async def delete(self, conversation: Conversation) -> None: ...

    async def commit(self) -> None: ...

    async def refresh(self, conversation: Conversation) -> None: ...


class ConversationStore(Protocol):
    """会话服务端口：上层（api/agent）取会话、建会话、读历史。

    实现由基础设施提供（PostgresConversationStore）——会话存取的
    DB 细节（Conversation 表 + checkpoint）都在实现侧。
    """

    async def get_or_create(
        self,
        session: ConversationSession,
        conversation_id: str | None,
        user_id: UUID | None,
    ) -> tuple[Conversation, bool]: ...

    async def get_recent(
        self,
        session: ConversationSession,
        user_id: UUID | None,
    ) -> Conversation | None: ...

    async def get_history_messages(self, thread_id: str) -> list[dict]: ...
