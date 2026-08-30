"""异步任务请求参数：api → Celery 任务 → worker 执行体 之间的输入契约。

与 domain/types.py 的领域模型区分：TaskParams/AdjustParams 是任务层的输入
序列化（PlanRequest.model_dump()），由 tasks.executor/worker 消费，domain
不引用。API 边界用 Pydantic（schemas.py），此处为落库 JSONB 的 plain dict 结构。
"""

from typing import NotRequired, TypedDict

from backend.domain.types import SpotDict


class TaskParams(TypedDict):
    """异步任务请求参数（PlanRequest.model_dump() 序列化，存 plan_tasks.request_params JSONB）。

    字段与 schemas.PlanRequest 对齐；cost_matrix/dist_matrix 可选
    （suggest 阶段结果复用，传入则跳过驾车 API 拉取）。
    """

    city: str
    hotel_name: str
    hotel_lon: float
    hotel_lat: float
    hotel_tw_start: float
    hotel_tw_end: float
    day_start: int
    min_days: int | None
    spots: list[dict]
    mode: str
    n_days: int | None
    penalty_weight: float
    early_wait_weight: float
    late_return_weight: float
    cost_matrix: NotRequired[list[list[float]]]
    dist_matrix: NotRequired[list[list[float]]]


class AdjustParams(TypedDict):
    """方案调整（add_poi）任务请求参数。

    与 TaskParams 不同：基于已有方案快照（PlanResult），而不是从零规划的
    PlanRequest。spots 为 PlanResult.spots（dict[int, SpotDict]），并携带
    当前 routes 与 adjustments 指令。cost_matrix/dist_matrix 为快照矩阵。
    """

    city: str
    spots: dict[int, SpotDict]
    cost_matrix: list[list[float]]
    dist_matrix: list[list[float]]
    routes: list[list[int]]
    adjustments: dict
