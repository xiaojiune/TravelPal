"""方案调整编排（pipeline.adjust_plan）· 移除景点分支测试。"""

import pytest

from backend.engine.pipeline import adjust_plan


class TestRemovePoi:
    """remove_poi 分支：移除指定景点并重新求解（不触网）。"""

    def test_remove_poi_excludes_target(self, base_adjust_plan):
        """remove_poi：生成的每日行程不再包含被移除的景点。"""
        spots, cost_mat, routes = base_adjust_plan
        target_name = next(spots[i]["name"] for i in spots if i != 0)

        plan = adjust_plan(spots, cost_mat.tolist(), cost_mat.tolist(), routes, {"remove_poi": target_name})

        all_names = {item["name"] for day in plan["daily_schedules"] for item in day}
        assert target_name not in all_names
        assert plan["solution"]["valid"] is True
        assert plan["commentary"]

    def test_remove_poi_unknown_raises(self, base_adjust_plan):
        """remove_poi：目标景点不存在时抛出 ValueError。"""
        spots, cost_mat, routes = base_adjust_plan

        with pytest.raises(ValueError, match="未找到景点"):
            adjust_plan(spots, cost_mat.tolist(), cost_mat.tolist(), routes, {"remove_poi": "不存在的景点"})
