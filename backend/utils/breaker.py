"""通用熔断器：简单半开状态熔断，防下游依赖雪崩。

与十重试(tenacity)配合：tenacity 做**单次调用的瞬时错误重试**，本熔断器做
**跨调用的持续失败保护**（连续失败超阈值→短暂熔断，快速失败不打下游；
熔断到期后放一个探测请求，成功则关闭）。

依赖方向：utils 零依赖（纯状态机，无 IO），供 data/infrastructure 等层复用。
"""

import time


class CircuitBreaker:
    """简单熔断器（含半开状态）。

    Args:
        fail_threshold: 连续失败多少次后熔断。
        open_seconds: 熔断持续秒数，到期后半开（放一个探测请求）。
        fail_fast_msg: 熔断期间快速失败抛出的异常消息前缀。

    Attributes:
        state: "closed"（正常）/ "open"（熔断）/ "half_open"（探测中）。
    """

    def __init__(self, fail_threshold: int = 3, open_seconds: float = 30, fail_fast_msg: str = "熔断") -> None:
        self.fail_threshold = fail_threshold
        self.open_seconds = open_seconds
        self.fail_fast_msg = fail_fast_msg
        self._fail_count = 0
        self._open_until = 0.0
        self.state = "closed"

    def allow(self) -> bool:
        """当前是否允许发起请求。

        Returns:
            bool: True 允许（closed/half_open）；False 处于熔断期（open）。
        """
        if self.state == "open" and time.monotonic() >= self._open_until:
            # 熔断到期 → 半开，放一个探测请求
            self.state = "half_open"
            return True
        return self.state != "open"

    def success(self) -> None:
        """调用成功：重置失败计数并关闭熔断。"""
        self._fail_count = 0
        self.state = "closed"

    def failure(self) -> None:
        """调用失败：累加失败计数，到达阈值则打开熔断。"""
        if self.state == "half_open":
            # 半开探测失败 → 重新熔断
            self._fail_count = self.fail_threshold
        else:
            self._fail_count += 1
        if self._fail_count >= self.fail_threshold:
            self.state = "open"
            self._open_until = time.monotonic() + self.open_seconds

    def get_state(self) -> str:
        """当前状态（closed/open/half_open），供观测/调试。"""
        return self.state
