"""方案调整编排（pipeline.adjust_plan）· adjust_days 分支回归测试。

adjust_days 分支已在 adjust_plan 收敛时移除（改天数能力将由 suggest 阶段
CA 多解缓存替代，见 adjust_plan_days 的 @refactor TODO）——本文件断言该
指令现在被拒绝，而非静默执行旧逻辑。
"""

import pytest

from backend.engine.pipeline import adjust_plan


class TestAdjustDaysRemoved:
    """adjust_days 分支已移除：传入该指令应抛 ValueError。"""

    def test_adjust_days_changes_days_rejected(self, base_adjust_plan):
        """adjust_days 指令现在被识别为未支持并抛出 ValueError。"""
        spots, cost_mat, routes = base_adjust_plan

        with pytest.raises(ValueError, match="未识别的调整指令"):
            adjust_plan(spots, cost_mat.tolist(), cost_mat.tolist(), routes, {"adjust_days": 3})

    def test_adjust_days_to_one_rejected(self, base_adjust_plan):
        """adjust_days=1 同样被拒绝。"""
        spots, cost_mat, routes = base_adjust_plan

        with pytest.raises(ValueError, match="未识别的调整指令"):
            adjust_plan(spots, cost_mat.tolist(), cost_mat.tolist(), routes, {"adjust_days": 1})

    def test_unknown_adjustment_raises(self, base_adjust_plan):
        """adjustments 未识别指令类型时抛出 ValueError。"""
        spots, cost_mat, routes = base_adjust_plan

        with pytest.raises(ValueError, match="未识别的调整指令"):
            adjust_plan(spots, cost_mat.tolist(), cost_mat.tolist(), routes, {"bogus": True})
