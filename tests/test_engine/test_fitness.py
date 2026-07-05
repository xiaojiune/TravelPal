import pytest
import numpy as np
from backend.engine.fitness import analyze_solution


class TestFitness:
    """适应度函数的成本分量与边界条件验证"""

    def test_basic_cost_components(self, n20_dataset):
        spots, dist_mat, _ = n20_dataset
        depot = 0
        route = [0, 1, 2, 0]

        cost, dist, wait_pen, late_pen, violations = analyze_solution(
            route, dist_mat, spots, travel_speed=1.0,
            early_wait_weight=0.1, penalty_weight=100.0,
            late_return_weight=50.0, depot=depot
        )

        assert cost > 0, "成本应大于 0"
        assert dist >= 0, "距离应非负"
        assert wait_pen >= 0, "等待惩罚应非负"
        assert late_pen >= 0, "迟到惩罚应非负"
        assert isinstance(violations, list)

    def test_no_penalty_when_perfect_timing(self):
        spots = {
            0: {"name": "depot", "tw": (0, 1000), "stay": 0},
            1: {"name": "A", "tw": (10, 100), "stay": 5},
            2: {"name": "B", "tw": (20, 200), "stay": 10},
        }
        dist_mat = np.array([
            [0, 10, 1],
            [10, 0, 5],
            [1, 5, 0],
        ], dtype=np.float64)
        route = [0, 1, 2, 0]

        cost, dist, wait_pen, late_pen, violations = analyze_solution(
            route, dist_mat, spots, travel_speed=1.0,
            early_wait_weight=0.1, penalty_weight=100.0,
            late_return_weight=50.0, depot=0
        )

        assert wait_pen == 0, f"不应有等待惩罚: {wait_pen}"
        assert late_pen == 0, f"不应有迟到惩罚: {late_pen}"
        assert len(violations) == 0, f"不应有违规: {violations}"

    def test_early_arrival_incurs_wait_penalty(self):
        spots = {
            0: {"name": "depot", "tw": (0, 1000), "stay": 0},
            1: {"name": "A", "tw": (100, 200), "stay": 0},
        }
        dist_mat = np.array([
            [0, 1],
            [1, 0],
        ], dtype=np.float64)
        route = [0, 1, 0]

        _, _, wait_pen, _, _ = analyze_solution(
            route, dist_mat, spots, travel_speed=1.0,
            early_wait_weight=0.5, penalty_weight=100.0,
            late_return_weight=50.0, depot=0
        )

        assert wait_pen > 0, f"早到应有等待惩罚: {wait_pen}"
        assert abs(wait_pen - (100 - 1) * 0.5) < 1e-6, (
            f"等待惩罚计算错误: wait_pen={wait_pen}, "
            f"预期={(100 - 1) * 0.5}"
        )

    def test_late_arrival_incurs_penalty(self):
        spots = {
            0: {"name": "depot", "tw": (0, 1000), "stay": 0},
            1: {"name": "A", "tw": (10, 20), "stay": 0},
        }
        dist_mat = np.array([
            [0, 50],
            [50, 0],
        ], dtype=np.float64)
        route = [0, 1, 0]

        _, _, _, late_pen, violations = analyze_solution(
            route, dist_mat, spots, travel_speed=1.0,
            early_wait_weight=0.1, penalty_weight=50.0,
            late_return_weight=50.0, depot=0
        )

        assert late_pen > 0, f"迟到应有惩罚: {late_pen}"
        assert len(violations) > 0, "应记录违规节点"

    def test_depot_stay_no_penalty(self):
        spots = {
            0: {"name": "depot", "tw": (0, 1000), "stay": 0},
            1: {"name": "A", "tw": (10, 500), "stay": 10},
        }
        dist_mat = np.array([
            [0, 10],
            [10, 0],
        ], dtype=np.float64)
        route = [0, 1, 0]

        cost, dist, wait_pen, late_pen, violations = analyze_solution(
            route, dist_mat, spots, travel_speed=1.0,
            early_wait_weight=0.1, penalty_weight=100.0,
            late_return_weight=50.0, depot=0
        )

        assert wait_pen == 0, f"不应有等待: {wait_pen}"
        assert late_pen == 0, f"不应有迟到: {late_pen}"
        assert cost > 0
