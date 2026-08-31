"""CircuitBreaker 熔断器单元测试（纯单元，不依赖外部服务）。

覆盖熔断器核心状态机：closed → open（连续失败阈值）→ half_open（熔断到期探测）
→ closed（探测成功）/ 重新 open（探测失败），以及熔断期快速失败。
"""

import time

from backend.utils.breaker import CircuitBreaker


def test_closed_initial():
    """初始为 closed，allow() 应为 True。"""
    b = CircuitBreaker(fail_threshold=3, open_seconds=30)
    assert b.get_state() == "closed"
    assert b.allow() is True


def test_opens_after_fail_threshold():
    """连续失败达到阈值后熔断（open），allow() 为 False。"""
    b = CircuitBreaker(fail_threshold=3, open_seconds=30)
    b.failure()
    assert b.allow() is True
    b.failure()
    assert b.allow() is True
    b.failure()
    assert b.get_state() == "open"
    assert b.allow() is False


def test_fast_fail_during_open():
    """熔断期内 allow() 持续为 False（快速失败，不打下游）。"""
    b = CircuitBreaker(fail_threshold=3, open_seconds=30)
    for _ in range(3):
        b.failure()
    # 还未到期
    assert b.allow() is False
    assert b.allow() is False


def test_half_open_success_closes():
    """熔断到期后 half_open：放探测请求，成功则 closed。"""
    b = CircuitBreaker(fail_threshold=3, open_seconds=0.05)
    for _ in range(3):
        b.failure()
    assert b.get_state() == "open"
    time.sleep(0.06)  # 等待熔断到期
    # 到期后 allow() -> half_open，放探测
    assert b.allow() is True
    assert b.get_state() == "half_open"
    b.success()
    assert b.get_state() == "closed"
    assert b.allow() is True


def test_half_open_failure_reopens():
    """half_open 探测失败则重新 open（重新熔断）。"""
    b = CircuitBreaker(fail_threshold=3, open_seconds=0.05)
    for _ in range(3):
        b.failure()
    assert b.get_state() == "open"
    time.sleep(0.06)
    assert b.allow() is True  # 进入 half_open
    assert b.get_state() == "half_open"
    b.failure()  # 半开探测失败
    assert b.get_state() == "open"
    assert b.allow() is False


def test_success_resets_fail_count():
    """成功调用重置失败计数，不因历史失败误熔断。"""
    b = CircuitBreaker(fail_threshold=3, open_seconds=30)
    b.failure()
    b.failure()
    b.success()  # 中途成功，计数清零
    assert b.get_state() == "closed"
    b.failure()
    assert b.allow() is True  # 还未到阈值
