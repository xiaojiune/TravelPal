"""规划工具：提交异步规划任务 + 查询任务结果（双工具，复用异步任务表）。

设计说明：
- get_plan 是重工具（驾车 API 拉取 + CA/VNS 求解可达分钟级），不能同步阻塞
  MCP/内部 FC 调用方，故复用轴 4 异步任务表：提交任务立即返回 task_id，
  由 Celery worker 后台执行。
- get_plan_result 供调用方轮询任务状态，result 仅 done 时存在。
- 两个工具均为 async：写 plan_tasks 表需 async SQLAlchemy 会话，
  MCP 与内部 FC 分发层均已支持 async 工具调用。
"""

from uuid import UUID

from backend.data.model.database import async_session
from backend.data.model.models import PlanTask
from backend.tasks.submit import submit_task


async def get_plan(
    city: str,
    hotel_name: str,
    hotel_lon: float,
    hotel_lat: float,
    spots: list[dict],
    n_days: int,
    mode: str = "fast",
    day_start: int = 480,
    hotel_tw_start: int = 0,
    hotel_tw_end: int = 1440,
    penalty_weight: float = 100.0,
    early_wait_weight: float = 0.1,
    late_return_weight: float = 50.0,
    min_days: int | None = None,
    cost_matrix: list[list[float]] | None = None,
    dist_matrix: list[list[float]] | None = None,
) -> dict:
    """提交一个完整行程规划任务，立即返回 task_id 供轮询。

    参数与后端 PlanRequest 全量对齐。spots 每项含 name/lon/lat/tw_start/tw_end/stay
    （由调用方先经 poi_lookup 获取坐标与营业时间；缺 tw_start/tw_end/stay 将直接
    失败，不填默认值）。cost_matrix/dist_matrix 可选，
    不传时 worker 内自动拉取驾车 API 构建成本矩阵（耗时较长，由异步任务消化）。

    Args:
        city: 城市名。
        hotel_name: 酒店名称。
        hotel_lon: 酒店经度（GCJ-02）。
        hotel_lat: 酒店纬度。
        spots: 景点列表，每项 { name, lon, lat, tw_start?, tw_end?, stay?, expected_arrival? }。
        n_days: 行程天数（必填）。
        mode: 求解模式，"fast"(CA) 或 "deep"(VNS)。
        day_start: 一天启程时间（距午夜分钟数），默认 480（08:00）。
        hotel_tw_start: 酒店时间窗开始（分钟），默认 0。
        hotel_tw_end: 酒店时间窗结束（分钟），默认 1440。
        penalty_weight: 迟到惩罚权重。
        early_wait_weight: 早到等待惩罚权重。
        late_return_weight: 晚归惩罚权重。
        min_days: 最小天数（建议模式用，指定 n_days 时忽略）。
        cost_matrix: 可选成本矩阵（分钟），复用 suggest 阶段结果跳过驾车 API。
        dist_matrix: 可选距离矩阵（km），与 cost_matrix 一同传入。

    Returns:
        dict: { task_id: str, status: "pending" }，供 get_plan_result 轮询。
        提交失败时返回 { error: str }。
    """
    params = {
        "city": city,
        "hotel_name": hotel_name,
        "hotel_lon": hotel_lon,
        "hotel_lat": hotel_lat,
        "hotel_tw_start": hotel_tw_start,
        "hotel_tw_end": hotel_tw_end,
        "day_start": day_start,
        "min_days": min_days,
        "spots": spots,
        "n_days": n_days,
        "mode": mode,
        "penalty_weight": penalty_weight,
        "early_wait_weight": early_wait_weight,
        "late_return_weight": late_return_weight,
    }
    if cost_matrix is not None and dist_matrix is not None:
        params["cost_matrix"] = cost_matrix
        params["dist_matrix"] = dist_matrix
    try:
        task_id = await submit_task("plan", params)
        return {"task_id": task_id, "status": "pending"}
    except Exception as e:
        return {"error": str(e)}


async def submit_plan_form(
    form_context: dict | None = None,
    n_days: int | None = None,
    mode: str = "fast",
) -> dict:
    """基于表单上下文提交规划任务（表单驱动版规划入口）。

    LLM 不拼参数：form_context 由编排层注入（前端 send() 携带首页表单快照），
    后端从中构造 PlanRequest 提交 suggest/plan 异步任务。n_days 缺失时按 suggest
    （自动推断天数），指定时按 plan（mode 决定 CA/VNS）。

    Args:
        form_context: 表单输入快照（编排层注入），含 city/hotel_name/hotel_lon/
            hotel_lat/hotel_tw_start/hotel_tw_end/day_start/min_days/spots
            {name,lon,lat,tw_start,tw_end,stay,expected_arrival}/惩罚权重。
        n_days: 行程天数。缺失 → suggest（自动推断）；指定 → plan。
        mode: 求解模式，"fast"(CA) 或 "deep"(VNS)，仅指定 n_days 时生效。

    Returns:
        dict: { task_id: str, status: "pending" }，供 get_plan_result 轮询；
        无 form_context 时返回 { error: "请先在首页填写城市/酒店/景点" }。
    """
    if not form_context:
        return {"error": "请先在首页填写城市/酒店/景点"}
    try:
        params = {
            "city": form_context.get("city", ""),
            "hotel_name": form_context.get("hotel_name", ""),
            "hotel_lon": form_context.get("hotel_lon", 0),
            "hotel_lat": form_context.get("hotel_lat", 0),
            "hotel_tw_start": form_context.get("hotel_tw_start", 0),
            "hotel_tw_end": form_context.get("hotel_tw_end", 1440),
            "day_start": form_context.get("day_start", 480),
            "min_days": form_context.get("min_days"),
            "spots": form_context.get("spots", []),
            "penalty_weight": form_context.get("penalty_weight", 100.0),
            "early_wait_weight": form_context.get("early_wait_weight", 0.1),
            "late_return_weight": form_context.get("late_return_weight", 50.0),
        }
        if n_days is not None:
            params["n_days"] = n_days
            params["mode"] = mode
            task_type = "plan"
        else:
            task_type = "suggest"
        task_id = await submit_task(task_type, params)
        return {"task_id": task_id, "status": "pending"}
    except Exception as e:
        return {"error": str(e)}


async def get_plan_result(task_id: str) -> dict:
    """查询异步规划任务的执行状态与结果。

    调用方应在 get_plan 拿到 task_id 后周期性轮询本工具，直到 status 为 done/failed。

    Args:
        task_id: get_plan 返回的任务 UUID 字符串。

    Returns:
        dict: { task_id, status, result?, error? }。
        status 为 pending/running/done/failed；result 仅 done 时存在（完整 PlanResult），
        error 仅 failed 时存在。任务不存在时返回 { error: "task not found" }。
    """
    try:
        async with async_session() as session:
            task = await session.get(PlanTask, UUID(task_id))
            if task is None:
                return {"error": "task not found"}
            return {
                "task_id": str(task.id),
                "status": task.status,
                "result": task.result,
                "error": task.error,
            }
    except Exception as e:
        return {"error": str(e)}
