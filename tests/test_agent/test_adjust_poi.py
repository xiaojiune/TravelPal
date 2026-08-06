"""add_poi 工具（双路径）契约测试。

覆盖：缺 plan 报错、快照不完整报错、停留时间三层降级、
同步快路径（点对缓存全命中直接重排）、异步路径（未命中提交 adjust 任务）。
不触网：monkeypatch 掉 driving_cache 与 submit_task。
"""

import asyncio

from backend.agent.tools import adjust
from backend.agent.tools.poi import estimate_stay


def _plan_snapshot() -> dict:
    """构造最小可用方案快照（spots/solution/cost_matrix/dist_matrix/routes）。"""
    return {
        "spots": {
            "0": {"name": "酒店", "x": 113.3, "y": 23.1, "tw": [0, 1440], "stay": 0},
            "1": {"name": "广州塔", "x": 113.32, "y": 23.1, "tw": [570, 1350], "stay": 180},
        },
        "solution": {"routes": [[0, 1, 0]]},
        "cost_matrix": [[0.0, 10.0], [10.0, 0.0]],
        "dist_matrix": [[0.0, 5.0], [5.0, 0.0]],
    }


def test_missing_plan_returns_error():
    result = asyncio.run(adjust.add_poi("广州", {"name": "白云山", "lon": 113.3, "lat": 23.2}))
    assert "error" in result and "缺少当前方案" in result["error"]


def test_incomplete_snapshot_returns_error():
    plan = _plan_snapshot()
    del plan["cost_matrix"]
    result = asyncio.run(adjust.add_poi("广州", {"name": "白云山", "lon": 113.3, "lat": 23.2}, plan=plan))
    assert "error" in result and "快照不完整" in result["error"]


def test_estimate_stay_explicit_wins():
    stay = asyncio.run(estimate_stay("spot", "白云山", explicit_stay=45))
    assert stay == 45


def test_estimate_stay_fallback_mapping():
    stay = asyncio.run(estimate_stay("spot", "白云山", context=None, explicit_stay=None))
    assert stay == 90


def test_estimate_stay_fallback_by_name():
    stay = asyncio.run(estimate_stay("facility", "星巴克咖啡", context=None, explicit_stay=None))
    assert stay == 45


def test_add_poi_sync_fast_path(monkeypatch):
    """点对缓存全命中 → 同步直接重排，返回完整方案。"""
    plan = _plan_snapshot()
    fake_result = {"solution": {"routes": [[0, 1, 2, 0]]}, "best_days": 1}

    monkeypatch.setattr(adjust, "get_driving_pair", lambda *a, **k: {"duration_min": 10.0, "distance_km": 5.0})

    captured = {}

    def fake_adjust_plan(spots, cost, dist, routes, adjustments, city=""):
        captured["adjustments"] = adjustments
        return fake_result

    monkeypatch.setattr("backend.engine.pipeline.adjust_plan", fake_adjust_plan)

    def _should_not_submit(*a, **k):
        raise AssertionError("不应提交异步任务")

    monkeypatch.setattr(adjust, "submit_task", _should_not_submit)

    result = asyncio.run(
        adjust.add_poi(
            "广州",
            {"name": "白云山", "lon": 113.3, "lat": 23.2, "poi_type": "spot"},
            plan=plan,
        )
    )
    assert result is fake_result
    assert captured["adjustments"]["add_poi"]["name"] == "白云山"


def test_add_poi_async_submit_when_cache_miss(monkeypatch):
    """缓存未命中 → 提交 adjust 异步任务，返回 task_id/pending。"""
    plan = _plan_snapshot()

    monkeypatch.setattr(adjust, "get_driving_pair", lambda *a, **k: None)

    async def fake_submit(task_type, params):
        assert task_type == "adjust"
        assert params["city"] == "广州"
        assert params["adjustments"]["add_poi"]["name"] == "白云山"
        return "task-123"

    monkeypatch.setattr(adjust, "submit_task", fake_submit)

    result = asyncio.run(
        adjust.add_poi(
            "广州",
            {"name": "白云山", "lon": 113.3, "lat": 23.2, "poi_type": "spot"},
            plan=plan,
        )
    )
    assert result == {"task_id": "task-123", "status": "pending"}
