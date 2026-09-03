"""跨层异常定义：跨 domain / infrastructure / tasks 复用的异常。

TaskCancelled 是协作式取消哨兵：由 domain 的取消检查点（cancel_check）抛出、
tasks.worker 捕获。放在跨层共享的 utils 层，避免 domain↔tasks 之间循环导入；
作为单一来源，供各层 import。其余层特有异常应在各自层定义。
"""


class TaskCancelled(Exception):
    """协作式取消哨兵：任务执行中被用户取消时抛出。

    由 tasks.worker 的取消监视器触发，经 pipeline/amap_loader 的
    cancel_check 检查点往上抛，最终在 worker._execute_task 捕获并将
    plan_tasks.status 置为 canceled（终态，不写 error）。
    """


class TransientError(Exception):
    """瞬时错误哨兵：任务执行中遇到可重试的外部抖动时抛出。

    如数据库连接偶发失败、依赖服务瞬时不可用等。tasks.worker 用
    ``autoretry_for=(TransientError,)`` 自动重试（指数退避），
    与业务性失败（参数缺字段/引擎 bug，直接置 failed）区分。
    """
