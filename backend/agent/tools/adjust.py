"""方案调整工具：add_poi（向已有方案添加新 POI 并重排，双路径）。

同步快路径：新点与方案内所有已有点（含酒店）的驾车数据全部命中 Redis 点对缓存时，
直接复用矩阵组装并重排，立即返回完整方案（PlanResult）。
异步路径：存在未命中的点对时，提交 adjust 任务由 worker 拉取驾车数据后重排，
返回 {task_id, status} 供 get_plan_result 轮询。

停留时间三层降级：显式参数 → poi_type/名称关键词映射（poi.estimate_stay，
无对话上下文时跳过 LLM 直用映射）→ 默认值。

plan 参数（当前方案快照）由编排层注入：内部 FC 经 orchestrator 的 plan_result
注入；外部 MCP 调用方需显式传入。
"""

from typing import cast

from backend.data.driving_cache import get_driving_pair
from backend.tasks.submit import submit_task


async def _extract_poi(poi: dict) -> dict:
    """规范化 add_poi 指令中的新点信息。

    补齐缺失的停留时间（estimate_stay 映射兜底）与时间窗（默认 08:00-17:00）。

    Args:
        poi: 原始指令 {name, lon, lat, tw_start?, tw_end?, stay?, poi_type?}。

    Returns:
        dict: pipeline.add_poi 分支所需的 {name, lon, lat, tw_start, tw_end, stay}。
    """
    from backend.agent.tools.poi import estimate_stay

    stay = await estimate_stay(
        poi.get("poi_type", "spot"),
        poi.get("name", ""),
        explicit_stay=poi.get("stay"),
    )
    return {
        "name": poi["name"],
        "lon": poi["lon"],
        "lat": poi["lat"],
        "tw_start": poi.get("tw_start", 480),
        "tw_end": poi.get("tw_end", 1020),
        "stay": stay,
    }


async def add_poi(city: str, poi: dict, plan: dict | None = None) -> dict:
    """向已有方案添加新 POI 并重排全局路线（双路径：缓存命中同步 / 未命中异步）。

    Args:
        city: 所在城市。
        poi: 新点 {name, lon, lat, tw_start?, tw_end?, stay?, poi_type?}。
        plan: 当前方案快照（PlanResult：spots/routes/cost_matrix/dist_matrix），
            编排层注入或外部调用方显式传入。

    Returns:
        dict: 同步路径返回完整调整后方案（PlanResult）；
            异步路径返回 {task_id, status: "pending"} 供轮询；
            参数缺失或异常返回 {error: str}。
    """
    if not plan:
        return {"error": "缺少当前方案（plan），无法执行添加景点调整"}
    if not (plan.get("spots") and plan.get("solution") and plan.get("cost_matrix") and plan.get("dist_matrix")):
        return {"error": "方案快照不完整（需 spots/solution/cost_matrix/dist_matrix）"}
    poi = await _extract_poi(poi)
    poi_point = {"name": poi["name"], "lon": poi["lon"], "lat": poi["lat"]}

    # 同步快路径判定：新点 ↔ 全部已有点（含酒店）的驾车数据是否全部命中缓存
    all_hit = True
    for spot in plan["spots"].values():
        target = {"name": spot["name"], "lon": spot["x"], "lat": spot["y"]}
        if get_driving_pair(city, poi_point, target) is None:
            all_hit = False
            break

    if all_hit:
        from backend.engine.pipeline import adjust_plan

        try:
            return cast(
                dict,
                adjust_plan(
                    plan["spots"],
                    plan["cost_matrix"],
                    plan["dist_matrix"],
                    plan["solution"]["routes"],
                    {"add_poi": poi},
                    city=city,
                ),
            )
        except Exception as e:
            return {"error": str(e)}

    params = {
        "city": city,
        "spots": plan["spots"],
        "cost_matrix": plan["cost_matrix"],
        "dist_matrix": plan["dist_matrix"],
        "routes": plan["solution"]["routes"],
        "adjustments": {"add_poi": poi},
    }
    try:
        task_id = await submit_task("adjust", params)
        return {"task_id": task_id, "status": "pending"}
    except Exception as e:
        return {"error": str(e)}
