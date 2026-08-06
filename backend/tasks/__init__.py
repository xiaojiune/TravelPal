"""异步任务包：Celery 应用 + 任务提交/消费/执行分层。

解耦原 celery_app.py 单模块（ADR-010 #6）：
- app.py：Celery 应用实例与队列配置（基础设施层）
- submit.py：提交侧（submit_task），HTTP 端点与 MCP 工具的唯一依赖
- worker.py：消费侧（run_plan_task + 状态流转），Celery 适配 + event loop 桥接
- executors.py：任务执行体 + TASK_EXECUTORS 注册表（纯计算，不含 DB 状态流转）

演进式架构衔接：新增任务类型 = executors.py 加 1 个执行函数 + 注册 1 行，
提交侧与 worker 启动命令（-A backend.tasks.app）均无需改动。
"""

from backend.tasks import app, executors, submit, worker

__all__ = [
    "app",
    "executors",
    "submit",
    "worker",
]
