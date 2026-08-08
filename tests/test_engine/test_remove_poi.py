"""方案调整编排（pipeline.adjust_plan）· 移除景点分支测试。"""

import numpy as np
import pytest

from backend.agent.planning import remove_poi_from_day
from backend.engine.pipeline import adjust_plan


def _single_spot_plan():
    """构造单天单景点方案（删除该景点即删空该天）。"""
    spots = {
        0: {"name": "酒店", "x": 0.0, "y": 0.0, "tw": [0, 1440], "original_tw": [0, 1440], "stay": 0},
        1: {"name": "广州塔", "x": 1.0, "y": 0.0, "tw": [480, 1020], "original_tw": [480, 1020], "stay": 120},
    }
    cost = np.array([[0.0, 10.0], [10.0, 0.0]])
    routes = [[0, 1, 0]]
    return spots, cost, routes


class TestRemovePoi:
    """remove_poi 分支：移除指定景点并重新求解（不触网）。"""

    def test_remove_poi_excludes_target(self, base_adjust_plan):
        """remove_poi：指定天移除景点，该天不再包含被移除的景点。"""
        spots, cost_mat, routes = base_adjust_plan
        target_name = next(spots[i]["name"] for i in spots if i != 0)

        plan = adjust_plan(
            spots,
            cost_mat.tolist(),
            cost_mat.tolist(),
            routes,
            {"remove_poi": target_name, "day": 0},
        )

        all_names = {item["name"] for day in plan["daily_schedules"] for item in day}
        assert target_name not in all_names
        assert plan["solution"]["valid"] is True
        # 评语已从调整流程剥离（agent-tool 形态，返回 None）
        assert plan["commentary"] is None

    def test_remove_poi_missing_day_raises(self, base_adjust_plan):
        """remove_poi：未指定 day（用户意图未定前）抛 ValueError 驱动追问。"""
        spots, cost_mat, routes = base_adjust_plan
        target_name = next(spots[i]["name"] for i in spots if i != 0)

        with pytest.raises(ValueError, match="remove_poi 调整必须指定目标天"):
            adjust_plan(spots, cost_mat.tolist(), cost_mat.tolist(), routes, {"remove_poi": target_name})

    def test_remove_poi_unknown_raises(self, base_adjust_plan):
        """remove_poi：目标景点不存在时抛出 ValueError。"""
        spots, cost_mat, routes = base_adjust_plan

        with pytest.raises(ValueError, match="未找到景点"):
            adjust_plan(
                spots,
                cost_mat.tolist(),
                cost_mat.tolist(),
                routes,
                {"remove_poi": "不存在的景点", "day": 0},
            )


class TestRemovePoiEdge:
    """remove_poi 边界：删除酒店 / 删空天废弃。"""

    def test_remove_hotel_raises(self):
        """不能删除酒店（depot，索引 0）。"""
        spots, cost, routes = _single_spot_plan()
        with pytest.raises(ValueError, match="不能删除酒店"):
            remove_poi_from_day(spots, cost, cost, routes, "酒店", day=0)

    def test_remove_day_empties_discards_day(self):
        """单天删除后该天空 → 废弃该天（best_days - 1）+ UserWarning。"""
        spots, cost, routes = _single_spot_plan()

        with pytest.warns(UserWarning, match="该天已废弃"):
            plan = remove_poi_from_day(spots, cost, cost, routes, "广州塔", day=0)

        assert plan["best_days"] == 0
        assert plan["solution"]["valid"] is True

    def test_remove_from_day_keeps_other_days(self, base_adjust_plan):
        """双天方案删除目标天景点，非目标天的景点集合不变（索引重映射后）。"""
        spots, cost_mat, routes = base_adjust_plan
        assert len(routes) == 2
        # 目标天 = 第 0 天的第一个景点
        day0_nodes = [n for n in routes[0] if n != 0]
        target_name = spots[day0_nodes[0]]["name"]
        # 非目标天（第 1 天）的景点名称集合
        other_names = {spots[n]["name"] for n in routes[1] if n != 0}

        plan = remove_poi_from_day(spots, cost_mat, cost_mat, routes, target_name, day=0)

        assert plan["solution"]["valid"] is True
        assert plan["best_days"] == 2
        # 用 daily_schedules 的第 1 天行程名称断言（索引已重映射；过滤酒店虚行）
        result_other = {
            item["name"] for item in plan["daily_schedules"][1] if item["name"] not in ("酒店（出发）", "酒店（返回）")
        }
        assert result_other == other_names
