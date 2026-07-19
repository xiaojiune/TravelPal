"""后端内部数据模型的 TypedDict 定义。

API 边界用 Pydantic（schemas.py），内部数据传递用 TypedDict。
TypedDict 零运行时开销，只做类型约束，可平滑升级为 Pydantic Model。
"""

from typing import NotRequired, TypedDict


class SpotDict(TypedDict):
    """景点/酒店在引擎内部的数据结构。

    x/y 为 GCJ-02 坐标，tw 为 (start, end) 分钟数对。
    """

    name: str
    x: float
    y: float
    tw: tuple[float, float]
    stay: float
    original_tw: tuple[float, float]
    lon: NotRequired[float]
    lat: NotRequired[float]
    expected_arrival: NotRequired[float]


class PoiCacheItem(TypedDict):
    """POI 缓存中单个条目，来自前端或 LLM 解析。"""

    name: str
    lon: float
    lat: float
    tw: tuple[float, float]
    stay: float
    address: NotRequired[str]
    expected_arrival: NotRequired[float]


class PoiCache(TypedDict):
    """前端传入的完整 POI 缓存，含酒店和景点列表。"""

    hotel: PoiCacheItem
    spots: list[PoiCacheItem]


class RouteResult(TypedDict):
    """solve_groups / balance_groups 的求解结果。"""

    routes: list[list[int]]
    histories: list[list[float]]
    total_cost: float
    total_dist: float
    wait: float
    late: float
    valid: bool


class ClusterResult(TypedDict):
    """cluster_and_solve 的返回结果。type="suggestion" 时无 solution。"""

    type: str
    solution: NotRequired[RouteResult]
    best_days: int
    best_m: str


class ScheduleItem(TypedDict):
    """每日行程中的一条记录。"""

    name: str
    arrival: int
    departure: int
    tw: str
    stay: str
    arrival_status: str
    departure_status: str


class PlanResult(TypedDict):
    """run_planning / adjust_plan 的完整返回。"""

    solution: RouteResult
    mode: str
    best_days: int
    best_m: str
    spots: dict[int, SpotDict]
    dataset_name: str
    algo_time: float
    daily_schedules: list[list[ScheduleItem]]
    cost_matrix: list[list[float]]
    dist_matrix: list[list[float]]
    polylines: dict[str, str]
    commentary: str
    amap_api_key: NotRequired[str]
    amap_security_code: NotRequired[str]
