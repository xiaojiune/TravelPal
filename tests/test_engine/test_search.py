import pytest
from src.engine.search import cluster_and_solve


class TestClusterAndSolve:
    def test_fast_mode_specified_days(self, n20_dataset):
        spots, dist_mat, _ = n20_dataset
        depot = 0

        result = cluster_and_solve(
            spots, depot, dist_mat, mode="fast", n_days=3,
            penalty_weight=100.0, early_wait_weight=0.1,
            late_return_weight=50.0,
        )

        assert "solution" in result
        assert "best_k" in result
        assert result["best_k"] == 3
        assert result["solution"]["total_cost"] > 0
        assert result["solution"]["valid"]

    def test_deep_mode_specified_days(self, n20_dataset):
        spots, dist_mat, _ = n20_dataset
        depot = 0

        result = cluster_and_solve(
            spots, depot, dist_mat, mode="deep", n_days=3,
            penalty_weight=100.0, early_wait_weight=0.1,
            late_return_weight=50.0,
        )

        assert result["best_k"] == 3
        assert result["solution"]["valid"]

    def test_fast_mode_auto_days(self, n20_dataset):
        spots, dist_mat, _ = n20_dataset
        depot = 0

        result = cluster_and_solve(
            spots, depot, dist_mat, mode="fast",
            min_clusters=2, max_clusters=4,
            penalty_weight=100.0, early_wait_weight=0.1,
            late_return_weight=50.0,
        )

        assert 2 <= result["best_k"] <= 4
        assert result["solution"]["total_cost"] > 0
        assert result["solution"]["valid"]

    def test_deep_mode_auto_days(self, n20_dataset):
        spots, dist_mat, _ = n20_dataset
        depot = 0

        result = cluster_and_solve(
            spots, depot, dist_mat, mode="deep",
            min_clusters=2, max_clusters=4,
            penalty_weight=100.0, early_wait_weight=0.1,
            late_return_weight=50.0,
        )

        assert 2 <= result["best_k"] <= 4
        assert result["solution"]["valid"]

    def test_routes_cover_all_nodes(self, n20_dataset):
        spots, dist_mat, _ = n20_dataset
        depot = 0
        spot_ids = set(spots.keys()) - {depot}

        for mode in ("fast", "deep"):
            result = cluster_and_solve(
                spots, depot, dist_mat, mode=mode, n_days=3,
                penalty_weight=100.0, early_wait_weight=0.1,
                late_return_weight=50.0,
            )

            visited = set()
            for route in result["solution"]["routes"]:
                for c in route:
                    if c != depot:
                        visited.add(c)

            assert visited == spot_ids, (
                f"{mode}: 遗漏节点 {spot_ids - visited}"
            )

    def test_daily_routes_valid(self, n20_dataset):
        spots, dist_mat, _ = n20_dataset
        depot = 0

        for mode in ("fast", "deep"):
            result = cluster_and_solve(
                spots, depot, dist_mat, mode=mode, n_days=3,
                penalty_weight=100.0, early_wait_weight=0.1,
                late_return_weight=50.0,
            )

            for route in result["solution"]["routes"]:
                assert route[0] == depot, f"{mode}: 路线应以 depot 开始"
                assert route[-1] == depot, f"{mode}: 路线应以 depot 结束"
                assert len(route) >= 3, f"{mode}: 至少需包含 depot-景点-depot"

    @pytest.mark.slow
    def test_on_larger_dataset(self, n60_dataset):
        spots, dist_mat, _ = n60_dataset
        depot = 0

        for mode in ("fast", "deep"):
            result = cluster_and_solve(
                spots, depot, dist_mat, mode=mode, n_days=3,
                penalty_weight=100.0, early_wait_weight=0.1,
                late_return_weight=50.0,
            )

            assert result["solution"]["total_cost"] > 0
            assert result["solution"]["valid"]
