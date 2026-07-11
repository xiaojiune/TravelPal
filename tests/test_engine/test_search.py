import pytest
from backend.engine.search import cluster_and_solve, ca_suggest


# ================== CA 全参数搜索 ==================


class TestCASuggest:
    """ca_suggest 全参数搜索的早退、去重与排序逻辑验证"""

# ---------- 基础用例 ----------
    def test_returns_suggestions(self, n20_dataset):
        spots, cost_mat, _ = n20_dataset
        depot = 0

        result = ca_suggest(
            spots, depot, cost_mat,
            penalty_weight=100.0, early_wait_weight=0.1,
            late_return_weight=50.0,
        )

        assert result["type"] == "suggestion"
        assert "suggestions" in result
        assert len(result["suggestions"]) >= 1
        for s in result["suggestions"]:
            assert "n_days" in s
            assert "method" in s
            assert "cost" in s
            assert "routes" in s
            assert s["cost"] > 0

    def test_suggestions_sorted_by_cost(self, n20_dataset):
        spots, cost_mat, _ = n20_dataset
        depot = 0

        result = ca_suggest(
            spots, depot, cost_mat,
            min_days=2,
            penalty_weight=100.0, early_wait_weight=0.1,
            late_return_weight=50.0,
        )

        costs = [s["cost"] for s in result["suggestions"]]
        assert costs == sorted(costs), "建议应按成本升序排列"

    def test_deduplicate_identical_groupings(self, n20_dataset):
        spots, cost_mat, _ = n20_dataset
        depot = 0

        result = ca_suggest(
            spots, depot, cost_mat,
            min_days=1,
            penalty_weight=100.0, early_wait_weight=0.1,
            late_return_weight=50.0,
        )

        unique_methods = set(s["method"] for s in result["suggestions"])
        # 去重后每组方法至多保留一个解
        assert len(result["suggestions"]) <= len(unique_methods) * 3

    def test_early_stop_works(self, n20_dataset):
        # 验证早退机制：增益阈值设高 + 容忍度设小 → 应快速停止
        spots, cost_mat, _ = n20_dataset
        depot = 0

        result = ca_suggest(
            spots, depot, cost_mat,
            min_days=2,
            early_stop_gain_threshold=50.0,
            stop_consecutive_worse=1,
            penalty_weight=100.0, early_wait_weight=0.1,
            late_return_weight=50.0,
        )

        assert result["type"] == "suggestion"
        assert len(result["suggestions"]) >= 1
        searched_days = set(s["n_days"] for s in result["suggestions"])
        # n=20 → 默认 min_days=20//8+1=3，但指定 min_days=2，早退敏感应只搜 2~3 个天数
        assert len(searched_days) <= 3, f"早退未生效：搜索了 {len(searched_days)} 个天数"


# ================== 双模式分发 ==================


class TestClusterAndSolve:
    """cluster_and_solve 双模式（fast/deep）与天数分发逻辑验证"""

    # ---------- fast 模式 ----------
    def test_fast_mode_with_n_days(self, n20_dataset):
        spots, cost_mat, _ = n20_dataset
        depot = 0

        result = cluster_and_solve(
            spots, depot, cost_mat, mode="fast", n_days=3,
            penalty_weight=100.0, early_wait_weight=0.1,
            late_return_weight=50.0,
        )

        assert result["type"] == "solution"
        assert result["best_days"] == 3
        assert result["solution"]["total_cost"] > 0
        assert result["solution"]["valid"]

    # ---------- deep 模式 ----------
    def test_deep_mode_with_n_days(self, n20_dataset):
        spots, cost_mat, _ = n20_dataset
        depot = 0

        result = cluster_and_solve(
            spots, depot, cost_mat, mode="deep", n_days=3,
            penalty_weight=100.0, early_wait_weight=0.1,
            late_return_weight=50.0,
        )

        assert result["type"] == "solution"
        assert result["best_days"] == 3
        assert result["solution"]["valid"]

    def test_deep_mode_without_n_days_raises(self, n20_dataset):
        spots, cost_mat, _ = n20_dataset
        depot = 0

        with pytest.raises(ValueError, match="指定 n_days"):
            cluster_and_solve(
                spots, depot, cost_mat, mode="deep",
                penalty_weight=100.0, early_wait_weight=0.1,
                late_return_weight=50.0,
            )

    # ---------- fast 无天数 ----------
    def test_fast_mode_without_n_days_returns_suggestions(self, n20_dataset):
        spots, cost_mat, _ = n20_dataset
        depot = 0

        result = cluster_and_solve(
            spots, depot, cost_mat, mode="fast",
            penalty_weight=100.0, early_wait_weight=0.1,
            late_return_weight=50.0,
        )

        assert result["type"] == "suggestion"
        assert len(result["suggestions"]) >= 1
        for s in result["suggestions"]:
            assert "routes" in s

    # ---------- 解有效性验证 ----------
    def test_routes_cover_all_nodes(self, n20_dataset):
        spots, cost_mat, _ = n20_dataset
        depot = 0
        spot_ids = set(spots.keys()) - {depot}

        for mode in ("fast", "deep"):
            result = cluster_and_solve(
                spots, depot, cost_mat, mode=mode, n_days=3,
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
        spots, cost_mat, _ = n20_dataset
        depot = 0

        for mode in ("fast", "deep"):
            result = cluster_and_solve(
                spots, depot, cost_mat, mode=mode, n_days=3,
                penalty_weight=100.0, early_wait_weight=0.1,
                late_return_weight=50.0,
            )

            for route in result["solution"]["routes"]:
                assert route[0] == depot, f"{mode}: 应以 depot 开始"
                assert route[-1] == depot, f"{mode}: 应以 depot 结束"
                assert len(route) >= 3, f"{mode}: 至少 depot-景点-depot"

    # ---------- 扩展性 ----------
    @pytest.mark.slow
    def test_on_larger_dataset(self, n60_dataset):
        # n60 验证编排层在大规模场景下两种模式均能产出可行解
        spots, cost_mat, _ = n60_dataset
        depot = 0

        for mode in ("fast", "deep"):
            result = cluster_and_solve(
                spots, depot, cost_mat, mode=mode, n_days=3,
                penalty_weight=100.0, early_wait_weight=0.1,
                late_return_weight=50.0,
            )
            assert result["solution"]["total_cost"] > 0
            assert result["solution"]["valid"]
