"""方案调整编排（pipeline.adjust_plan）· 改天数分支测试。"""

import pytest

from backend.engine.pipeline import adjust_plan


class TestAdjustDays:
    """adjust_days 分支：保持景点不变，按新天数重新规划（不触网）。"""

    def test_adjust_days_changes_days(self, base_adjust_plan):
        """adjust_days：天数改为 3 后返回结构完整且每日行程为 3 天。"""
        spots, cost_mat, routes = base_adjust_plan

        plan = adjust_plan(spots, cost_mat.tolist(), cost_mat.tolist(), routes, {"adjust_days": 3})

        assert plan["mode"] == "adjust"
        assert plan["best_days"] == 3
        assert len(plan["daily_schedules"]) == 3
        assert plan["solution"]["valid"] is True
        assert plan["commentary"]

    def test_adjust_days_to_one(self, base_adjust_plan):
        """adjust_days：压缩到 1 天也能产出合法单日行程。"""
        spots, cost_mat, routes = base_adjust_plan

        plan = adjust_plan(spots, cost_mat.tolist(), cost_mat.tolist(), routes, {"adjust_days": 1})

        assert plan["best_days"] == 1
        assert len(plan["daily_schedules"]) == 1
        assert plan["solution"]["valid"] is True

    def test_unknown_adjustment_raises(self, base_adjust_plan):
        """adjustments 未识别指令类型时抛出 ValueError。"""
        spots, cost_mat, routes = base_adjust_plan

        with pytest.raises(ValueError, match="未识别的调整指令"):
            adjust_plan(spots, cost_mat.tolist(), cost_mat.tolist(), routes, {"bogus": True})
