"""remove_poi 工具（双路径）契约测试。

覆盖：缺 plan 报错、快照不完整报错、day 缺失（意图未定→全局）、
day 指定（单日）、同步失败异步兜底。
不触网：monkeypatch 掉 pipeline.adjust_plan 与 submit_task。
"""

import asyncio

from backend.agent.tools import remove as remove_tool


def _plan_snapshot() -> dict:
    """构造最小可用方案快照（spots/solution/cost_matrix/dist_matrix，2 天）。"""
    return {
        "spots": {
            "0": {"name": "酒店", "x": 113.3, "y": 23.1, "tw": [0, 1440], "stay": 0},
            "1": {"name": "广州塔", "x": 113.32, "y": 23.1, "tw": [570, 1350], "stay": 180},
            "2": {"name": "白云山", "x": 113.3, "y": 23.2, "tw": [480, 1020], "stay": 120},
        },
        "solution": {"routes": [[0, 1, 0], [0, 2, 0]]},
        "cost_matrix": [[0.0, 10.0, 8.0], [10.0, 0.0, 6.0], [8.0, 6.0, 0.0]],
        "dist_matrix": [[0.0, 5.0, 4.0], [5.0, 0.0, 3.0], [4.0, 3.0, 0.0]],
    }


def test_missing_plan_returns_error():
    result = asyncio.run(remove_tool.remove_poi("广州", "广州塔"))
    assert "error" in result and "缺少当前方案" in result["error"]


def test_incomplete_snapshot_returns_error():
    plan = _plan_snapshot()
    del plan["dist_matrix"]
    result = asyncio.run(remove_tool.remove_poi("广州", "广州塔", plan=plan))
    assert "error" in result and "快照不完整" in result["error"]


def test_remove_poi_day_specified_passes_day(monkeypatch):
    """day 指定 → adjustments 携带 day（单日重排）。"""
    plan = _plan_snapshot()
    fake_result = {"solution": {"routes": [[0, 0], [0, 2, 0]]}, "best_days": 2}

    captured = {}

    def fake_adjust_plan(spots, cost, dist, routes, adjustments, city=""):
        captured["adjustments"] = adjustments
        return fake_result

    monkeypatch.setattr("backend.engine.pipeline.adjust_plan", fake_adjust_plan)

    def _should_not_submit(*a, **k):
        raise AssertionError("同步成功不应提交异步任务")

    monkeypatch.setattr(remove_tool, "submit_task", _should_not_submit)

    result = asyncio.run(remove_tool.remove_poi("广州", "广州塔", day=0, plan=plan))
    assert result is fake_result
    assert captured["adjustments"] == {"remove_poi": "广州塔", "day": 0}


def test_remove_poi_missing_day_global(monkeypatch):
    """day 缺失（意图未定）→ adjustments 不含 day（全局重排）。"""
    plan = _plan_snapshot()
    fake_result = {"solution": {"routes": [[0, 2, 0], [0, 0]]}, "best_days": 2}

    captured = {}

    def fake_adjust_plan(spots, cost, dist, routes, adjustments, city=""):
        captured["adjustments"] = adjustments
        return fake_result

    monkeypatch.setattr("backend.engine.pipeline.adjust_plan", fake_adjust_plan)

    result = asyncio.run(remove_tool.remove_poi("广州", "广州塔", plan=plan))
    assert result is fake_result
    assert captured["adjustments"] == {"remove_poi": "广州塔"}


def test_remove_poi_sync_failure_submits_async(monkeypatch):
    """同步失败（如 day 越界）→ 异步兜底提交 adjust 任务。"""
    plan = _plan_snapshot()

    def fake_adjust_plan(*a, **k):
        raise ValueError("day 越界")

    monkeypatch.setattr("backend.engine.pipeline.adjust_plan", fake_adjust_plan)

    async def fake_submit(task_type, params):
        assert task_type == "adjust"
        assert params["adjustments"] == {"remove_poi": "广州塔", "day": 5}
        return "task-999"

    monkeypatch.setattr(remove_tool, "submit_task", fake_submit)

    result = asyncio.run(remove_tool.remove_poi("广州", "广州塔", day=5, plan=plan))
    assert result == {"task_id": "task-999", "status": "pending"}
