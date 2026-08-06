"""任务提交侧：创建 plan_tasks 记录并投递 Celery 队列。

被 HTTP 端点（/api/suggest、/api/plan）与 MCP 工具（get_plan）共同复用，
是提交任务的唯一入口。submit_task 只依赖 data/model 与 worker 的任务对象，
不依赖引擎——提交与执行解耦，新增任务类型无需改本模块。
"""

from backend.data.model.database import async_session
from backend.data.model.models import PlanTask


async def submit_task(task_type: str, params: dict) -> str:
    """创建异步任务记录并投递到 Celery 队列。

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
        from backend.tasks.worker import run_plan_task

        run_plan_task.delay(str(task.id))  # type: ignore[attr-defined]
        return str(task.id)
