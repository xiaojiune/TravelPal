"""方案调整 · 添加景点函数测试（直接测 planner.add_poi_to_plan，不经触网编排）。"""

from backend.agent.planning import add_poi_to_plan


class TestAddPoi:
    """add_poi_to_plan：向方案添加景点并重新求解的调用契约。"""

    def test_add_poi_returns_valid_plan(self, base_adjust_plan):
        """以当前矩阵调用 add_poi 重新求解，返回结构与基准天数一致。"""
        spots, cost_mat, routes = base_adjust_plan

        plan = add_poi_to_plan(spots, cost_mat, cost_mat, routes)

        assert plan["solution"]["valid"] is True
        assert plan["best_days"] == len(routes) == 2
        assert plan["best_m"] == "add_poi"
        assert len(plan["daily_schedules"]) == len(routes)
