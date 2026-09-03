"""Celery 应用实例与队列配置（基础设施层）。

worker 启动入口：`celery -A backend.tasks.app worker`。
import 本模块会连带加载 tasks/__init__ 中的 worker.py，保证任务注册。
"""

from celery import Celery
from kombu import Queue

from backend.config import settings

celery_app = Celery("travelpal", broker=settings.CELERY_BROKER_URL)

# 队列与死信交换机声明：
# - plan：任务主队列。执行失败经 autoretry_for 重试，重试耗尽或不可重试的失败
#   经 x-dead-letter-exchange 路由到 x-dead（死信交换机）→ plan.dead 死信队列，
#   供运维排查"反复失败"的任务（对应 ops 规范：队列堆积/失败率告警）。
# - plan.dead：死信队列，接收超重试次数的失败消息。
# LavinMQ(AMQP 0-9-1) 支持 x-dead-letter-exchange / x-dead-letter-routing-key。
_default_exchange = "travelpal"
celery_app.conf.task_default_queue = "plan"
celery_app.conf.task_default_exchange = _default_exchange
celery_app.conf.task_default_routing_key = "plan"

task_queues = (
    Queue(
        "plan",
        routing_key="plan",
        queue_arguments={
            "x-dead-letter-exchange": "x-dead",
            "x-dead-letter-routing-key": "plan.dead",
        },
    ),
    Queue("plan.dead", routing_key="plan.dead"),
)

# 长任务队列配置说明：
# - task_acks_late: 任务执行完成后才 ack，worker 崩溃不丢任务（配合 at-least-once）
# - task_reject_on_worker_lost: worker 崩溃(如 OOM/被杀)时拒绝该任务，避免被错误 ack
# - worker_prefetch_multiplier=1: 单 worker 每次只取一个任务，避免长任务堆积抢占
# - task_time_limit / task_soft_time_limit: 硬/软超时上限（超时由任务侧幂等判断兜底）
celery_app.conf.update(
    task_queues=task_queues,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_time_limit=900,
    task_soft_time_limit=840,
)

__all__ = ["celery_app", "task_queues"]
