import pytest
from src.engine.search import cluster_and_solve, ca_suggest


class TestCASuggest:
    def test_returns_suggestions(self, n20_dataset):
        spots, dist_mat, _ = n20_dataset
        depot = 0

        result = ca_suggest(
            spots, depot, dist_mat,
            penalty_weight=100.0, early_wait_weight=0.1,
            late_return_weight=50.0,
        )

        assert result["type"] == "suggestion"
        assert "suggestions" in result
        assert 1 <= len(result["suggestions"]) <= 5
        for s in result["suggestions"]:
            assert "k" in s
            assert "method" in s
            assert "cost" in s
            assert s["cost"] > 0

    def test_suggestions_sorted_by_cost(self, n20_dataset):
        spots, dist_mat, _ = n20_dataset
        depot = 0

        result = ca_suggest(
            spots, depot, dist_mat,
            min_clusters=2, max_clusters=4,
            penalty_weight=100.0, early_wait_weight=0.1,
            late_return_weight=50.0,
        )

        costs = [s["cost"] for s in result["suggestions"]]
        assert costs == sorted(costs), "建议应按成本升序排列"

    def test_deduplicate_identical_groupings(self, n20_dataset):
        spots, dist_mat, _ = n20_dataset
        depot = 0

        result = ca_suggest(
            spots, depot, dist_mat,
            min_clusters=1, max_clusters=1,
            penalty_weight=100.0, early_wait_weight=0.1,
            late_return_weight=50.0,
        )

        unique_methods = set(s["method"] for s in result["suggestions"])
        assert len(result["suggestions"]) <= len(unique_methods)


class TestClusterAndSolve:
    def test_fast_mode_with_n_days(self, n20_dataset):
        spots, dist_mat, _ = n20_dataset
        depot = 0

        result = cluster_and_solve(
            spots, depot, dist_mat, mode="fast", n_days=3,
            penalty_weight=100.0, early_wait_weight=0.1,
            late_return_weight=50.0,
        )

        assert result["type"] == "solution"
        assert result["best_k"] == 3
        assert result["solution"]["total_cost"] > 0
        assert result["solution"]["valid"]

    def test_deep_mode_with_n_days(self, n20_dataset):
        spots, dist_mat, _ = n20_dataset
        depot = 0

        result = cluster_and_solve(
            spots, depot, dist_mat, mode="deep", n_days=3,
            penalty_weight=100.0, early_wait_weight=0.1,
            late_return_weight=50.0,
        )

        assert result["type"] == "solution"
        assert result["best_k"] == 3
        assert result["solution"]["valid"]

    def test_deep_mode_without_n_days_raises(self, n20_dataset):
        spots, dist_mat, _ = n20_dataset
        depot = 0

        with pytest.raises(ValueError, match="指定 n_days"):
            cluster_and_solve(
                spots, depot, dist_mat, mode="deep",
                penalty_weight=100.0, early_wait_weight=0.1,
                late_return_weight=50.0,
            )

    def test_fast_mode_without_n_days_returns_suggestions(self, n20_dataset):
        spots, dist_mat, _ = n20_dataset
        depot = 0

        result = cluster_and_solve(
            spots, depot, dist_mat, mode="fast",
            penalty_weight=100.0, early_wait_weight=0.1,
            late_return_weight=50.0,
        )

        assert result["type"] == "suggestion"
        assert len(result["suggestions"]) >= 1

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
            assert visited == spot_ids, f"{mode}: 遗漏节点 {spot_ids - visited}"

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
                assert route[0] == depot, f"{mode}: 应以 depot 开始"
                assert route[-1] == depot, f"{mode}: 应以 depot 结束"
                assert len(route) >= 3, f"{mode}: 至少 depot-景点-depot"

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
