"""任务消费侧：Celery 任务入口 + plan_tasks 状态流转。

run_plan_task 是 worker 执行入口（含 asyncpg 跨 loop 适配），
_execute_task 负责状态流转并按 task_type 分发到 TASK_EXECUTORS。
"""

import asyncio
import time
import traceback
from datetime import datetime, timezone
from uuid import UUID

from backend.config import settings
from backend.data.model.database import async_session, engine
from backend.data.model.models import PlanTask
from backend.observability import task_duration, task_total
from backend.tasks.app import celery_app
from backend.tasks.executors import TASK_EXECUTORS
from backend.typedefs import TaskParams


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

    分发：按 task_type 从 TASK_EXECUTORS 取执行函数（未知类型触发 KeyError → failed）。
    """
    async with async_session() as session:
        task = await session.get(PlanTask, UUID(task_id))
        if task is None:
            return

        task_type = task.task_type  # type: ignore[assignment]
        start = time.monotonic()
        task.status = "running"  # type: ignore[assignment]
        task.started_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        await session.commit()

        try:
            executor = TASK_EXECUTORS[task_type]  # type: ignore[index]
            params: TaskParams = task.request_params  # type: ignore[assignment]
            result = executor(params)
            result["amap_api_key"] = settings.AMAP_JS_KEY  # type: ignore[index]
            result["amap_security_code"] = settings.AMAP_JS_SECURITY_CODE  # type: ignore[index]
            task.status = "done"  # type: ignore[assignment]
            task.result = result  # type: ignore[assignment]
        except Exception as e:
            traceback.print_exc()
            task.status = "failed"  # type: ignore[assignment]
            task.error = str(e)  # type: ignore[assignment]
        finally:
            task.finished_at = datetime.now(timezone.utc)  # type: ignore[assignment]
            await session.commit()
            # 任务耗时与结果指标（worker 进程侧，经 multiprocess 聚合到 /api/metrics）
            status = "success" if task.status == "done" else "failed"  # type: ignore[comparison-overlap]
            task_total.labels(task_type=task_type, status=status).inc()
            task_duration.labels(task_type=task_type).observe(time.monotonic() - start)
