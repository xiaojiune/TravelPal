"""方案调整 · 添加景点单日重排测试（直接测 planning.add_poi_to_day，不经触网编排）。"""

import numpy as np
import pytest

from backend.agent.planning import add_poi_to_day


def _expand(spots, cost_mat, name="新景点", stay=60) -> tuple[dict, np.ndarray, int]:
    """在 spots 中加入新点并展开矩阵（模拟 pipeline add_poi 分支的矩阵扩展）。"""
    import copy

    new_spots = copy.deepcopy(spots)
    new_idx = len(new_spots)
    new_spots[new_idx] = {
        "name": name,
        "x": 113.33,
        "y": 23.13,
        "tw": (480, 1020),
        "original_tw": (480, 1020),
        "stay": stay,
    }
    n = len(new_spots)
    new_cost = np.full((n, n), 0.0, dtype=np.float64)
    new_cost[: n - 1, : n - 1] = cost_mat
    return new_spots, new_cost, new_idx


class TestAddPoiToDay:
    """add_poi_to_day：向指定天添加景点并只重排该天的调用契约。"""

    def test_add_poi_to_day_keeps_other_days(self, base_adjust_plan):
        """只重排目标天，其余天路线原样保留。"""
        spots, cost_mat, routes = base_adjust_plan
        assert len(routes) == 2
        before_other = routes[1]  # 非目标天（目标天=0）路线

        new_spots, new_cost, new_idx = _expand(spots, cost_mat)
        plan = add_poi_to_day(new_spots, new_cost, new_cost, routes, new_idx, day=0)

        assert plan["solution"]["valid"] is True
        assert plan["best_days"] == 2
        assert plan["best_m"] == "add_poi"
        # 目标天包含新点
        assert new_idx in plan["solution"]["routes"][0]
        # 其余天路线完全不变
        assert plan["solution"]["routes"][1] == before_other
        assert len(plan["daily_schedules"]) == 2

    def test_add_poi_to_day_targets_middle_day(self, base_adjust_plan):
        """指定中间天（day=1）时新点进入该天且它天不变。"""
        spots, cost_mat, routes = base_adjust_plan
        assert len(routes) == 2
        before_day0 = routes[0]

        new_spots, new_cost, new_idx = _expand(spots, cost_mat)
        plan = add_poi_to_day(new_spots, new_cost, new_cost, routes, new_idx, day=1)

        assert new_idx in plan["solution"]["routes"][1]
        assert plan["solution"]["routes"][0] == before_day0
        assert plan["solution"]["valid"] is True

    def test_add_poi_to_day_out_of_range_raises(self, base_adjust_plan):
        """day 越界抛 ValueError（确定性优先：不自动归位）。"""
        spots, cost_mat, routes = base_adjust_plan
        new_spots, new_cost, new_idx = _expand(spots, cost_mat)
        with pytest.raises(ValueError, match="超出范围"):
            add_poi_to_day(new_spots, new_cost, new_cost, routes, new_idx, day=5)

    def test_add_poi_to_day_negative_raises(self, base_adjust_plan):
        """day 为负数同样拒绝。"""
        spots, cost_mat, routes = base_adjust_plan
        new_spots, new_cost, new_idx = _expand(spots, cost_mat)
        with pytest.raises(ValueError, match="超出范围"):
            add_poi_to_day(new_spots, new_cost, new_cost, routes, new_idx, day=-1)
