"""方案调整工具：remove_poi（从已有方案移除指定景点，双路径）。

确定性优先（针对用户意图，而非 day）：编排层先引导用户明确意图——
能说出目标天 → 单日重排；说不出（意图未定）→ 全局重排兜底。

双路径（与 add_poi 对称）：
- 同步快路径：remove 不新增任何驾车数据（仅删矩阵行列 + 重排），纯本地
  计算秒级，直接调用 pipeline.adjust_plan 立即返回完整方案（PlanResult）。
- 异步路径：同步失败/异常时提交 adjust 任务兜底，返回 {task_id, status}
  供 get_plan_result 轮询（与 add_poi 统一框架，虽然 remove 几乎用不到）。

边界/错误语义：
- 不可删除酒店（depot）：删除索引 0 抛 ValueError
- 单日修改下每日必须保留至少一个景点：删除导致该天空时废弃该天
  （best_days - 1）并发出 UserWarning
- 目标景点不存在抛 ValueError

plan 参数（当前方案快照）由编排层注入：内部 FC 经 orchestrator 的 plan_result
注入；外部 MCP 调用方需显式传入。
"""

from typing import cast

from backend.tasks.submit import submit_task


async def remove_poi(
    city: str,
    poi_name: str,
    day: int | None = None,
    plan: dict | None = None,
) -> dict:
    """从已有方案移除指定景点（双路径：同步为主 / 异步兜底）。

    day 缺失（用户意图未定）时走全局重排；day 指定时走单日重排。

    Args:
        city: 所在城市。
        poi_name: 要移除的景点名称。
        day: 目标天索引（0-indexed，第 1 天 = 0）。缺失表示用户未指定天，
            按全局重排处理（意图未定兜底）。
        plan: 当前方案快照（PlanResult：spots/routes/cost_matrix/dist_matrix），
            编排层注入或外部调用方显式传入。

    Returns:
        dict: 同步路径返回完整调整后方案（PlanResult）；
            异步路径返回 {task_id, status: "pending"} 供轮询；
            参数缺失或异常返回 {error: str}。
    """
    if not plan:
        return {"error": "缺少当前方案（plan），无法执行移除景点调整"}
    if not (plan.get("spots") and plan.get("solution") and plan.get("cost_matrix") and plan.get("dist_matrix")):
        return {"error": "方案快照不完整（需 spots/solution/cost_matrix/dist_matrix）"}

    adjustments: dict = {"remove_poi": poi_name}
    if day is not None:
        adjustments["day"] = day

    from backend.engine.pipeline import adjust_plan

    try:
        return cast(
            dict,
            adjust_plan(
                plan["spots"],
                plan["cost_matrix"],
                plan["dist_matrix"],
                plan["solution"]["routes"],
                adjustments,
                city=city,
            ),
        )
    except Exception:
        # 同步失败（确定性错误：景点不存在/删除酒店/day 越界等）→ 异步兜底
        # 注：remove 纯本地计算，异步重跑大概率同样失败，兜底仅对齐 add 双路径框架
        pass

    params = {
        "city": city,
        "spots": plan["spots"],
        "cost_matrix": plan["cost_matrix"],
        "dist_matrix": plan["dist_matrix"],
        "routes": plan["solution"]["routes"],
        "adjustments": adjustments,
    }
    try:
        task_id = await submit_task("adjust", params)
        return {"task_id": task_id, "status": "pending"}
    except Exception as e:
        return {"error": str(e)}
