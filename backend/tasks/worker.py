"""任务消费侧：Celery 任务入口 + plan_tasks 状态流转。

run_plan_task 是 worker 执行入口（含 asyncpg 跨 loop 适配），
_execute_task 负责状态流转并按 task_type 分发到 TASK_EXECUTORS。

协作式取消：
- 取消端点把 plan_tasks.status 置为 canceled；
- worker 执行前检测到 canceled 直接收尾（排队中被取消）；
- 执行中由 _watch_cancel 在 event loop 内每秒探测 status，见 canceled 即
  置位 threading.Event；executor 的 cancel_check 读取该 Event，在驾车 API
  逐段调用间抛 TaskCancelled（秒级中断），最终置 canceled 终态。
"""

import asyncio
import threading
import time
import traceback
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from backend.config import settings
from backend.infrastructure.data.model.database import async_session, engine
from backend.infrastructure.data.model.models import PlanTask
from backend.observability import task_duration, task_total
from backend.tasks.app import celery_app
from backend.tasks.executors import TASK_EXECUTORS
from backend.typedefs import TaskCancelled, TaskParams


@celery_app.task(name="travelpal.run_plan_task")
def run_plan_task(task_id: str) -> str:
    """异步规划任务入口：执行 or-ca 或 or-vns 求解，更新 plan_tasks 状态。

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
        canceled（执行前被取消或执行中由监护中断，不写 error）
        终态均写入 finished_at。

    协作式取消：
        executor 是同步纯计算，放默认线程池执行以释放 event loop，让
        _watch_cancel 守护协程能继续探测取消；否则循环被阻塞无法协作中断。
        cancel_check 读到 Event 置位即抛 TaskCancelled（由数据层/pipeline 抛出）。

    分发：按 task_type 从 TASK_EXECUTORS 取执行函数（未知类型触发 KeyError → failed）。
    """
    # 阶段1：读任务 + 前置取消检测 + 置 running（session 内取值，避免 detached 访问）
    async with async_session() as session:
        task = await session.get(PlanTask, UUID(task_id))
        if task is None:
            return
        task_type = task.task_type  # type: ignore[assignment]
        start = time.monotonic()
        if task.status == "canceled":  # type: ignore[comparison-overlap]
            # 排队中被取消：worker 尚未执行，直接收尾（不写 error）
            task.finished_at = datetime.now(timezone.utc)  # type: ignore[assignment]
            await session.commit()
            return
        task.status = "running"  # type: ignore[assignment]
        task.started_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        await session.commit()
        params: TaskParams = dict(task.request_params)  # type: ignore[assignment]

    # 阶段2：取消监护 + 线程池执行求解
    cancel_evt = threading.Event()
    watcher = asyncio.create_task(_watch_cancel(task_id, cancel_evt))
    try:
        executor = TASK_EXECUTORS[task_type]  # type: ignore[index]
        result = await asyncio.get_running_loop().run_in_executor(
            None, executor, params, cancel_evt.is_set
        )
        result["amap_api_key"] = settings.AMAP_JS_KEY  # type: ignore[index]
        result["amap_security_code"] = settings.AMAP_JS_SECURITY_CODE  # type: ignore[index]
        async with async_session() as session:
            task = await session.get(PlanTask, UUID(task_id))
            task.status = "done"  # type: ignore[assignment]
            task.result = result  # type: ignore[assignment]
            await session.commit()  # 状态改写必须提交，否则 async_session 退出回滚
    except TaskCancelled:
        traceback.print_exc()
        async with async_session() as session:
            task = await session.get(PlanTask, UUID(task_id))
            task.status = "canceled"  # type: ignore[assignment]
            await session.commit()
    except Exception as e:
        traceback.print_exc()
        async with async_session() as session:
            task = await session.get(PlanTask, UUID(task_id))
            task.status = "failed"  # type: ignore[assignment]
            task.error = str(e)  # type: ignore[assignment]
            await session.commit()
    finally:
        watcher.cancel()
        # 等监护协程彻底退出，避免与随后 engine.dispose() 冲突
        await asyncio.gather(watcher, return_exceptions=True)
        async with async_session() as session:
            task = await session.get(PlanTask, UUID(task_id))
            task.finished_at = datetime.now(timezone.utc)  # type: ignore[assignment]
            await session.commit()
            # 任务耗时与结果指标（worker 进程侧，经 multiprocess 聚合到 /api/metrics）
            status = "success" if task.status == "done" else "failed"  # type: ignore[comparison-overlap]
            task_total.labels(task_type=task_type, status=status).inc()
            task_duration.labels(task_type=task_type).observe(time.monotonic() - start)


async def _watch_cancel(task_id: str, cancel_evt: threading.Event) -> None:
    """协作式取消监护：探测 plan_tasks.status 是否被改为 canceled。

    发现 canceled → 置位 cancel_evt（executor 的 cancel_check 读取它，
    在驾车 API 逐段调用间抛 TaskCancelled，秒级中断）；否则每秒重查。
    任务结束由 _execute_task 的 finally 取消本协程。

    Args:
        task_id: plan_tasks 表主键（UUID 字符串）。
        cancel_evt: 与 executor 共享的取消事件（threading.Event 跨线程安全）。
    """
    try:
        while True:
            async with async_session() as session:
                row = await session.execute(
                    select(PlanTask.status).where(PlanTask.id == UUID(task_id))
                )
                status = row.scalar_one_or_none()
            if status == "canceled":
                cancel_evt.set()
                return
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        return
