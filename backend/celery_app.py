"""Celery 应用与异步规划任务定义。

设计说明：
- broker 使用 redis（docker-compose 已部署），worker 独立进程消费队列。
- 结果写库采用方案 A：任务内部直接更新 plan_tasks 表（复用 async SQLAlchemy），
  不配置 Celery result backend——GET /api/tasks/{id} 查询自有表，掌控力最强。
- run_planning 为同步阻塞函数（含驾车 API 拉取，suggest 可达 40s），在 worker
  进程内直接调用，不阻塞 Web 服务 event loop；DB 操作经 asyncio.run 桥接异步会话。
- task_type 区分 "suggest"（CA 建议）与 "plan"（指定天数求解），
  不同任务类型共享同一队列，未来 OR+AI/ML 架构演进时可按类型分流。
"""

import asyncio
import traceback
from datetime import datetime, timezone
from uuid import UUID

from celery import Celery

from backend.config import AMAP_JS_KEY, AMAP_JS_SECURITY_CODE, CELERY_BROKER_URL
from backend.data.model.database import async_session, engine
from backend.data.model.models import PlanTask

celery_app = Celery("travelpal", broker=CELERY_BROKER_URL)

# 长任务队列配置说明：
# - task_acks_late: 任务执行完成后才 ack，worker 崩溃不丢任务（配合 at-least-once）
# - worker_prefetch_multiplier=1: 单 worker 每次只取一个任务，避免长任务堆积抢占
celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=900,
    task_soft_time_limit=840,
)


def _build_poi_cache(params: dict):
    """将任务请求参数（PlanRequest.model_dump() 序列化）转换为 poi_cache 格式。

    任务运行在独立 worker 进程，直接消费 JSONB 中存储的 dict，
    不依赖 Pydantic 反序列化（避免 celery_app → api 包循环导入）。

    Args:
        params: 请求参数字典，字段与 PlanRequest 对齐（hotel_*/spots）。

    Returns:
        dict: {"hotel": {...酒店信息...}, "spots": [...景点列表...]}。
    """
    hotel = {
        "name": params["hotel_name"],
        "lon": params["hotel_lon"],
        "lat": params["hotel_lat"],
        "tw": (params["hotel_tw_start"], params["hotel_tw_end"]),
        "stay": 0,
    }
    spots = []
    for s in params["spots"]:
        spots.append(
            {
                "name": s["name"],
                "lon": s["lon"],
                "lat": s["lat"],
                "tw": (s["tw_start"], s["tw_end"]),
                "stay": s["stay"],
                "expected_arrival": s.get("expected_arrival"),
            }
        )
    return {"hotel": hotel, "spots": spots}


async def submit_task(task_type: str, params: dict) -> str:
    """创建异步任务记录并投递到 Celery 队列。

    被 HTTP 端点（/api/suggest、/api/plan）与 MCP 工具（get_plan）共同复用，
    是提交任务的唯一入口。任务记录写入 plan_tasks 表，worker 消费队列后执行。

    Args:
        task_type: 任务类型，固定 "suggest" 或 "plan"。
        params: 完整请求参数字典（PlanRequest 结构，含 hotel_*/spots/penalty 等）。

    Returns:
        str: 新创建任务的 UUID 字符串（供调用方返回 task_id）。

    Raises:
        Exception: 数据库写入失败时向上抛出，由调用方转为 HTTP 500 或工具 error。
    """
    async with async_session() as session:
        task = PlanTask(task_type=task_type, status="pending", request_params=params)
        session.add(task)
        await session.commit()
        run_plan_task.delay(str(task.id))  # type: ignore[attr-defined]
        return str(task.id)


@celery_app.task(name="travelpal.run_plan_task")
def run_plan_task(task_id: str) -> str:
    """异步规划任务入口：执行 suggest 或 plan 求解，更新 plan_tasks 状态。

    Args:
        task_id: plan_tasks 表主键（UUID 字符串）。

    Returns:
        str: 最终状态（"done" 或 "failed"）。

    设计说明：
    - 每次任务使用全新的 event loop 执行 async DB 操作，结束后 dispose 引擎
      清空连接池。原因：asyncpg 连接绑定创建它的 loop，Celery worker 是
      长期驻留进程，若复用模块级连接池，第二次任务会用新 loop 取到挂在
      旧 loop 上的连接，触发 "Future attached to a different loop" 错误。
    - 每次 dispose 会重建连接（毫秒级开销），相对任务本身（驾车 API 数十秒）
      可忽略，换来的是跨 loop 的健壮性。
    """
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_execute_task(task_id))
        loop.run_until_complete(engine.dispose())
    finally:
        loop.close()
    return "done"


async def _execute_task(task_id: str) -> None:
    """执行任务状态流转与规划求解（async 内部实现）。

    Args:
        task_id: plan_tasks 表主键（UUID 字符串）。

    状态流转：
        pending → running（开始执行时写入 started_at）
        running → done（成功，result 写入完整响应）
        running → failed（异常，error 写入错误信息）
        终态均写入 finished_at。
    """
    async with async_session() as session:
        task = await session.get(PlanTask, UUID(task_id))
        if task is None:
            return

        task.status = "running"  # type: ignore[assignment]
        task.started_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        await session.commit()

        try:
            from backend.engine.pipeline import run_planning

            params: dict = task.request_params  # type: ignore[assignment]
            # suggest 固定走 CA 建议模式；plan 沿用请求中的 mode/n_days
            is_suggest: bool = task.task_type == "suggest"  # type: ignore[operator]
            result = run_planning(
                _build_poi_cache(params),  # type: ignore[arg-type]
                params["city"],
                params["hotel_name"],
                penalty_weight=params["penalty_weight"],
                early_wait_weight=params["early_wait_weight"],
                late_return_weight=params["late_return_weight"],
                mode="fast" if is_suggest else params["mode"],
                n_days=None if is_suggest else params["n_days"],
                day_start=int(params["day_start"]),
                min_days=params.get("min_days"),
                cost_matrix_override=params.get("cost_matrix"),
                dist_matrix_override=params.get("dist_matrix"),
            )
            result["amap_api_key"] = AMAP_JS_KEY  # type: ignore[index]
            result["amap_security_code"] = AMAP_JS_SECURITY_CODE  # type: ignore[index]
            task.status = "done"  # type: ignore[assignment]
            task.result = result  # type: ignore[assignment]
        except Exception as e:
            traceback.print_exc()
            task.status = "failed"  # type: ignore[assignment]
            task.error = str(e)  # type: ignore[assignment]
        finally:
            task.finished_at = datetime.now(timezone.utc)  # type: ignore[assignment]
            await session.commit()
