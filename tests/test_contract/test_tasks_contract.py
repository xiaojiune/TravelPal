"""tasks 层契约测试：锁定任务执行注册表与参数转换契约。

契约测试：纯单元验证 backend/tasks 层的三个稳定契约，
防止拆分/重构（executors 增删、参数结构演进）时静默破坏：
- TASK_EXECUTORS 注册表 keys（suggest/plan/adjust）
- _build_poi_cache 参数转换契约（TaskParams → PoiCache，缺字段 ValueError）
- 各 executor 接受与返回的形状（纯函数不触网）

不依赖外部服务（postgres/redis/Celery），CI 零改动。
"""

import pytest

from backend.tasks.app import celery_app
from backend.tasks.executors import TASK_EXECUTORS, _build_poi_cache
from backend.utils.exceptions import TransientError


def _plan_params() -> dict:
    """构造一份完整的 plan 任务参数字典（对齐 PlanRequest.model_dump()）。"""
    return {
        "city": "广州",
        "hotel_name": "广州酒店",
        "hotel_lon": 113.3,
        "hotel_lat": 23.1,
        "hotel_tw_start": 0,
        "hotel_tw_end": 1440,
        "day_start": 480,
        "min_days": None,
        "penalty_weight": 100.0,
        "early_wait_weight": 0.1,
        "late_return_weight": 50.0,
        "mode": "fast",
        "n_days": 2,
        "spots": [
            {
                "name": "广州塔",
                "lon": 113.32,
                "lat": 23.1,
                "tw_start": 570,
                "tw_end": 1350,
                "stay": 180,
                "expected_arrival": 600,
            }
        ],
    }


class TestTaskExecutorsRegistry:
    """任务执行注册表契约。"""

    def test_registry_keys(self):
        assert set(TASK_EXECUTORS.keys()) == {"or-ca", "or-vns", "adjust"}

    def test_executors_are_callable(self):
        for fn in TASK_EXECUTORS.values():
            assert callable(fn)


class TestBuildPoiCache:
    """参数转换契约。"""

    def test_converts_hotel_and_spots(self):
        cache = _build_poi_cache(_plan_params())
        assert cache["hotel"]["name"] == "广州酒店"
        assert cache["hotel"]["tw"] == (0, 1440)
        assert cache["hotel"]["stay"] == 0
        assert len(cache["spots"]) == 1
        spot = cache["spots"][0]
        assert spot["name"] == "广州塔"
        assert spot["tw"] == (570, 1350)
        assert spot["stay"] == 180
        assert spot["expected_arrival"] == 600

    def test_missing_tw_raises_value_error(self):
        params = _plan_params()
        del params["spots"][0]["tw_start"]
        with pytest.raises(ValueError, match="广州塔"):
            _build_poi_cache(params)

    def test_missing_stay_raises_value_error(self):
        params = _plan_params()
        del params["spots"][0]["stay"]
        with pytest.raises(ValueError, match="广州塔"):
            _build_poi_cache(params)

    def test_expected_arrival_optional(self):
        params = _plan_params()
        del params["spots"][0]["expected_arrival"]
        cache = _build_poi_cache(params)
        assert "expected_arrival" not in cache["spots"][0]


class TestCeleryReliability:
    """Celery 可靠性配置契约：死信队列 / autoretry_for / 幂等判断。

    锁定想法3 的核心加固，防止未来改动退化：
    - 主队列带死信参数（失败超重试进 plan.dead）
    - 任务对 TransientError autoretry_for + 指数退避重试
    - _is_transient 区分瞬时/业务错误
    """

    def test_queues_plan_has_dead_letter(self):
        from backend.tasks.app import task_queues

        queues = {q.name: q for q in task_queues}
        assert "plan" in queues and "plan.dead" in queues
        args = queues["plan"].queue_arguments
        assert args["x-dead-letter-exchange"] == "x-dead"
        assert args["x-dead-letter-routing-key"] == "plan.dead"

    def test_run_plan_task_autoretry_for_transient(self):
        from backend.tasks.worker import run_plan_task

        assert run_plan_task.autoretry_for == (TransientError,)
        assert run_plan_task.max_retries == 3
        assert run_plan_task.retry_backoff is True

    def test_terminal_state_idempotent(self):
        from backend.tasks.worker import _is_transient

        # 瞬时错误应判 True，业务类 Exception 返回 False
        assert _is_transient(ConnectionError("conn reset")) is True
        assert _is_transient(ValueError("bad param")) is False
