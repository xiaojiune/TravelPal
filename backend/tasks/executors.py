"""任务执行体：参数校验 + 各任务类型求解 + 执行注册表。

executor 签名统一 `(params: TaskParams) -> dict`，纯计算不含 DB 状态流转
（状态流转由 worker._execute_task 统一负责）。
新增任务类型：实现一个 executor 函数 + TASK_EXECUTORS 注册 1 行。
run_planning 保持函数内延迟 import：worker 启动时不加载引擎，
也避免 executors → pipeline → agent → tools/plan → tasks/submit 的顶层环。
"""

from typing import Callable, cast

from backend.typedefs import PlanResult, PoiCache, PoiCacheItem, TaskParams

__all__ = ["TASK_EXECUTORS", "_build_poi_cache"]


def _build_poi_cache(params: TaskParams) -> PoiCache:
    """将任务请求参数（PlanRequest.model_dump() 序列化）转换为 poi_cache 格式。

    任务运行在独立 worker 进程，直接消费 JSONB 中存储的 dict，
    不依赖 Pydantic 反序列化（避免 tasks 包 → api 包循环导入）。

    Args:
        params: 请求参数字典，字段与 PlanRequest 对齐（hotel_*/spots）。

    Returns:
        PoiCache: {"hotel": {...酒店信息...}, "spots": [...景点列表...]}。

    Raises:
        ValueError: 景点缺少 tw_start/tw_end/stay 时抛出（缺默认值填掩盖错误）。
    """
    hotel: PoiCacheItem = {
        "name": params["hotel_name"],
        "lon": params["hotel_lon"],
        "lat": params["hotel_lat"],
        "tw": (params["hotel_tw_start"], params["hotel_tw_end"]),
        "stay": 0,
    }
    spots: list[PoiCacheItem] = []
    for s in params["spots"]:
        missing = [k for k in ("tw_start", "tw_end", "stay") if s.get(k) is None]
        if missing:
            raise ValueError(f"景点 '{s.get('name', '?')}' 缺少字段 {missing}，请先通过 poi_lookup 获取坐标与营业时间")
        spot: PoiCacheItem = {
            "name": s["name"],
            "lon": s["lon"],
            "lat": s["lat"],
            "tw": (s["tw_start"], s["tw_end"]),
            "stay": s["stay"],
        }
        expected = s.get("expected_arrival")
        if expected is not None:
            spot["expected_arrival"] = cast(float, expected)
        spots.append(spot)
    return PoiCache(hotel=hotel, spots=spots)


def _run_suggest(params: TaskParams) -> dict:
    """suggest 任务执行体：CA 建议模式（n_days=None，自动搜索天数）。

    Args:
        params: 请求参数字典（含 hotel_*/spots/penalty/day_start/min_days/cost_matrix 等）。

    Returns:
        dict: run_planning 建议分支完整结果（type="suggestion"，结构对应 schemas.SuggestResult）。
    """
    from backend.engine.pipeline import run_planning

    return run_planning(  # type: ignore[return-value]
        _build_poi_cache(params),
        params["city"],
        params["hotel_name"],
        penalty_weight=params["penalty_weight"],
        early_wait_weight=params["early_wait_weight"],
        late_return_weight=params["late_return_weight"],
        mode="fast",
        n_days=None,
        day_start=int(params["day_start"]),
        min_days=params.get("min_days"),
        cost_matrix_override=params.get("cost_matrix"),
        dist_matrix_override=params.get("dist_matrix"),
    )


def _run_plan(params: TaskParams) -> PlanResult:
    """plan 任务执行体：指定天数求解（mode=fast 用 CA / deep 用 VNS）。

    Args:
        params: 请求参数字典（含 hotel_*/spots/mode/n_days/day_start 等）。

    Returns:
        PlanResult: run_planning 求解分支完整结果（type="solution"）。
    """
    from backend.engine.pipeline import run_planning

    return cast(
        PlanResult,
        run_planning(
            _build_poi_cache(params),
            params["city"],
            params["hotel_name"],
            penalty_weight=params["penalty_weight"],
            early_wait_weight=params["early_wait_weight"],
            late_return_weight=params["late_return_weight"],
            mode=params["mode"],
            n_days=params["n_days"],
            day_start=int(params["day_start"]),
            min_days=params.get("min_days"),
            cost_matrix_override=params.get("cost_matrix"),
            dist_matrix_override=params.get("dist_matrix"),
        ),
    )


# 任务类型 → 执行函数注册表（worker._execute_task 按 task_type 分发）。
# suggest 返回 dict（结构对应 schemas.SuggestResult），plan 返回 PlanResult。
TASK_EXECUTORS: dict[str, Callable[[TaskParams], PlanResult | dict]] = {
    "suggest": _run_suggest,
    "plan": _run_plan,
}
