import pytest
from src.engine.search import sa_vns_pipeline
from src.engine.fitness import analyze_solution


class TestSearch:
    def test_pipeline_runs_on_small(self, n20_dataset):
        spots, dist_mat, _ = n20_dataset
        depot = 0

        result = sa_vns_pipeline(
            spots, depot, dist_mat, travel_speed=1.0,
            penalty_weight=100.0, early_wait_weight=0.1,
            late_return_weight=50.0, min_clusters=2, max_clusters=4
        )

        assert "sa_result" in result
        assert "vns_result" in result
        assert "best_k" in result
        assert "best_m" in result
        assert "improvement" in result

        assert 2 <= result["best_k"] <= 4, (
            f"best_k={result['best_k']} 应在 [2, 4] 范围内"
        )
        assert result["best_m"] is not None, "应选出最佳聚类方法"

    def test_pipeline_vns_improves_sa(self, n20_dataset):
        spots, dist_mat, _ = n20_dataset
        depot = 0

        result = sa_vns_pipeline(
            spots, depot, dist_mat, travel_speed=1.0,
            penalty_weight=100.0, early_wait_weight=0.1,
            late_return_weight=50.0, min_clusters=2, max_clusters=4
        )

        sa_cost = result["sa_result"]["total_cost"]
        vns_cost = result["vns_result"]["total_cost"]
        improvement = result["improvement"]

        assert vns_cost <= sa_cost + 1e-6, (
            f"VNS 成本 {vns_cost:.1f} 应不高于 SA {sa_cost:.1f}"
        )
        assert improvement >= -1e-6, f"提升率应非负: {improvement:.2f}%"

    def test_pipeline_routes_cover_all_nodes(self, n20_dataset):
        spots, dist_mat, _ = n20_dataset
        depot = 0
        spot_ids = set(spots.keys()) - {depot}

        result = sa_vns_pipeline(
            spots, depot, dist_mat, travel_speed=1.0,
            penalty_weight=100.0, early_wait_weight=0.1,
            late_return_weight=50.0, min_clusters=2, max_clusters=4
        )

        for label in ("sa_result", "vns_result"):
            visited = set()
            for route in result[label]["routes"]:
                for c in route:
                    if c != depot:
                        visited.add(c)
            assert visited == spot_ids, (
                f"{label}: 遗漏节点 {spot_ids - visited}"
            )

    def test_pipeline_daily_routes_valid(self, n20_dataset):
        spots, dist_mat, _ = n20_dataset
        depot = 0

        result = sa_vns_pipeline(
            spots, depot, dist_mat, travel_speed=1.0,
            penalty_weight=100.0, early_wait_weight=0.1,
            late_return_weight=50.0, min_clusters=2, max_clusters=4
        )

        for route in result["vns_result"]["routes"]:
            assert route[0] == depot, "每天路线应以 depot 开始"
            assert route[-1] == depot, "每天路线应以 depot 结束"
            assert len(route) >= 3, "每天至少需包含 depot-景点-depot"

    @pytest.mark.slow
    def test_pipeline_on_medium(self, n60_dataset):
        spots, dist_mat, _ = n60_dataset
        depot = 0

        result = sa_vns_pipeline(
            spots, depot, dist_mat, travel_speed=1.0,
            penalty_weight=100.0, early_wait_weight=0.1,
            late_return_weight=50.0, min_clusters=2, max_clusters=5
        )

        assert result["vns_result"]["total_cost"] > 0
        assert result["improvement"] >= -1e-6
