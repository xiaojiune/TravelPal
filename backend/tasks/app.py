"""Celery 应用实例与队列配置（基础设施层）。

worker 启动入口：`celery -A backend.tasks.app worker`。
import 本模块会连带加载 tasks/__init__ 中的 worker.py，保证任务注册。
"""

from celery import Celery

from backend.config import settings

celery_app = Celery("travelpal", broker=settings.CELERY_BROKER_URL)

# 长任务队列配置说明：
# - task_acks_late: 任务执行完成后才 ack，worker 崩溃不丢任务（配合 at-least-once）
# - worker_prefetch_multiplier=1: 单 worker 每次只取一个任务，避免长任务堆积抢占
celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=900,
    task_soft_time_limit=840,
)

__all__ = ["celery_app"]
