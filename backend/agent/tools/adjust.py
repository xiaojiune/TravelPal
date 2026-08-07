"""方案调整工具：add_poi（向已有方案指定天添加新 POI 并单日重排，双路径）。

确定性优先：day 为目标天索引（0-indexed，第 1 天 = 0），由编排层从对话明确
提取后传入。day 缺失时 schema 层（required）阻止调用，工具内再校验越界，
驱动 LLM 向用户追问，不自动执行、不猜测归属。

同步快路径：新点与目标天节点 + 酒店（depot）的驾车数据全部命中 Redis 点对
缓存时，直接复用矩阵组装并单日重排，立即返回完整方案（PlanResult）。
异步路径：存在未命中的点对时，提交 adjust 任务由 worker 拉取驾车数据后
重排，返回 {task_id, status} 供 get_plan_result 轮询。

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


def _target_day_nodes(routes: list, day: int) -> list[int]:
    """取目标天包含的核心节点（剥掉首尾 depot），并校验 day 范围。

    Args:
        routes: 方案路径列表，每组含首尾 depot。
        day: 目标天索引（0-indexed）。

    Returns:
        list[int]: 目标天的景点索引列表（不含 depot）。

    Raises:
        ValueError: day 越界或 routes 为空。
    """
    n_days = len(routes)
    if not routes:
        raise ValueError("方案无任何天，无法添加景点")
    if not 0 <= day < n_days:
        raise ValueError(f"目标天 day={day} 超出范围，方案共 {n_days} 天（第 1 天=0）")
    route = routes[day]
    return route[1:-1] if len(route) > 2 and route[0] == 0 else list(route)


async def add_poi(city: str, poi: dict, day: int, plan: dict | None = None) -> dict:
    """向已有方案指定天添加新 POI 并单日重排（双路径：缓存命中同步 / 未命中异步）。

    Args:
        city: 所在城市。
        poi: 新点 {name, lon, lat, tw_start?, tw_end?, stay?, poi_type?}。
        day: 目标天索引（0-indexed，第 1 天 = 0），必须明确，不自动猜测。
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

    # day 范围校验（确定性优先：越界不自动归位，抛出供 LLM 追问）
    try:
        target_nodes = _target_day_nodes(plan["solution"]["routes"], day)
    except ValueError as e:
        return {"error": str(e)}

    # 同步快路径判定：新点 ↔ 目标天节点 + 酒店(depot) 是否全部命中缓存
    hotel = plan["spots"]["0"]
    check_points = [{"name": hotel["name"], "lon": hotel["x"], "lat": hotel["y"]}]
    for idx in target_nodes:
        s = plan["spots"][str(idx)]
        check_points.append({"name": s["name"], "lon": s["x"], "lat": s["y"]})
    all_hit = all(get_driving_pair(city, poi_point, t) is not None for t in check_points)

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
                    {"add_poi": poi, "day": day},
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
        "adjustments": {"add_poi": poi, "day": day},
    }
    try:
        task_id = await submit_task("adjust", params)
        return {"task_id": task_id, "status": "pending"}
    except Exception as e:
        return {"error": str(e)}
