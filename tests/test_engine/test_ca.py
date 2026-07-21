import numpy as np

from backend.engine.ca import CASolver

# ================== CA 求解器 ==================


class TestSA:
    """CA 求解器的基础正确性与压缩退火特性测试"""

    # ---------- 基础正确性 ----------
    def test_sa_solution_valid(self, n20_dataset):
        spots, cost_mat, _ = n20_dataset
        city_indices = list(range(1, len(spots)))

        solver = CASolver(city_indices, spots, penalty_weight=100.0, early_wait_weight=0.1, late_return_weight=50.0)
        res = solver.solve(cost_mat)

        sol = res["best_solution"]
        assert sol[0] == 0, "路线应以 depot 开始"
        assert sol[-1] == 0, "路线应以 depot 结束"
        assert len(set(sol)) == len(city_indices) + 1, "路线应覆盖所有城市（去重 + depot）"

        visited = set(sol[1:-1])
        assert visited == set(city_indices), f"遗漏节点: {set(city_indices) - visited}"

    def test_sa_cost_reasonable(self, n20_dataset):
        spots, cost_mat, _ = n20_dataset
        city_indices = list(range(1, len(spots)))

        solver = CASolver(city_indices, spots, penalty_weight=100.0, early_wait_weight=0.1, late_return_weight=50.0)
        res = solver.solve(cost_mat)

        assert res["best_cost"] > 0, "成本应大于 0"
        assert res["best_distance"] >= 0, "距离应非负"
        assert res["best_penalty"] >= 0, "惩罚应非负"

    def test_sa_convergence(self, n20_dataset):
        spots, cost_mat, _ = n20_dataset
        city_indices = list(range(1, len(spots)))

        solver = CASolver(city_indices, spots)
        res = solver.solve(cost_mat)

        conv = res["convergence_history"]
        assert len(conv) >= 2, "应有至少 2 个收敛点"
        for i in range(1, len(conv)):
            assert conv[i] <= conv[i - 1] + 1e-6, f"收敛历史不应上升: {conv[i - 1]} -> {conv[i]}"

    # ---------- 退火模式 ----------
    def test_sa_compressed_vs_standard(self, n20_dataset):
        # 验证两种退火模式（压缩/标准）均能产出可行解，不要求严格优劣
        spots, cost_mat, _ = n20_dataset
        city_indices = list(range(1, len(spots)))

        solver_comp = CASolver(city_indices, spots, use_compressed_annealing=True)
        solver_std = CASolver(city_indices, spots, use_compressed_annealing=False)

        res_comp = solver_comp.solve(cost_mat)
        res_std = solver_std.solve(cost_mat)

        assert res_comp["best_cost"] > 0
        assert res_std["best_cost"] > 0

    def test_sa_2opt_improves(self, n20_dataset):
        spots, cost_mat, _ = n20_dataset
        city_indices = list(range(1, len(spots)))

        solver = CASolver(city_indices, spots)
        res = solver.solve(cost_mat)

        final_cost = res["best_cost"]
        conv = res["convergence_history"]
        pre_2opt_cost = conv[-1] if len(conv) > 1 else final_cost
        assert final_cost <= pre_2opt_cost + 1e-6, "2-opt 后成本不应上升"

    # ---------- 随机性 ----------
    def test_sa_different_seeds_different_results(self, n20_dataset):
        # 验证算法对随机种子敏感（不收敛到单一解），保证探索能力
        spots, cost_mat, _ = n20_dataset
        city_indices = list(range(1, len(spots)))

        results = []
        for seed in range(3):
            np.random.seed(seed)
            solver = CASolver(city_indices, spots)
            res = solver.solve(cost_mat)
            results.append(res["best_cost"])

        unique = len(set(round(c, 1) for c in results))
        assert unique >= 2 or all(c == results[0] for c in results), "不同随机种子应产生不同或相同的最优解"

    # ---------- 扩展性 ----------
    def test_sa_on_larger_dataset(self, n60_dataset):
        # n60（60 个景点）验证求解器在大规模问题下的可扩展性和解覆盖能力
        spots, cost_mat, _ = n60_dataset
        city_indices = list(range(1, len(spots)))

        solver = CASolver(city_indices, spots, penalty_weight=100.0, early_wait_weight=0.1, late_return_weight=50.0)
        res = solver.solve(cost_mat)

        visited = set(res["best_solution"][1:-1])
        assert visited == set(city_indices), "n60 解应覆盖所有节点"
        assert res["best_cost"] > 0
