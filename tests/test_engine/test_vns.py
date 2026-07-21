from backend.engine.ca import CASolver
from backend.engine.vns import VNSSolver

# ================== VNS 求解器 ==================


class TestVNS:
    """VNS 求解器的多起点收敛、精英池与 CA 对比验证"""

    # ---------- 基础正确性 ----------
    def test_vns_solution_valid(self, n20_dataset):
        spots, cost_mat, _ = n20_dataset
        city_indices = list(range(1, len(spots)))

        solver = VNSSolver(city_indices, spots, penalty_weight=100.0, early_wait_weight=0.1, late_return_weight=50.0)
        res = solver.solve(cost_mat)

        sol = res["best_solution"]
        assert sol[0] == 0, "路线应以 depot 开始"
        assert sol[-1] == 0, "路线应以 depot 结束"

        visited = set(sol[1:-1])
        assert visited == set(city_indices), f"遗漏节点: {set(city_indices) - visited}"

    def test_vns_improves_over_ca(self, n20_dataset):
        # 核心架构假设验证：VNS 以 CA 解为起点应能进一步优化或至少不劣化
        spots, cost_mat, _ = n20_dataset
        city_indices = list(range(1, len(spots)))

        ca = CASolver(city_indices, spots)
        vns = VNSSolver(city_indices, spots)

        ca_res = ca.solve(cost_mat)
        vns_res = vns.solve(cost_mat, initial_solution=ca_res["best_solution"])

        (ca_res["best_cost"] - vns_res["best_cost"]) / ca_res["best_cost"] * 100
        assert vns_res["best_cost"] <= ca_res["best_cost"] + 1e-6, (
            f"VNS 成本 {vns_res['best_cost']:.1f} 应不高于 CA 成本 {ca_res['best_cost']:.1f}"
        )

    def test_vns_elite_pool(self, n20_dataset):
        spots, cost_mat, _ = n20_dataset
        city_indices = list(range(1, len(spots)))

        solver = VNSSolver(city_indices, spots, elite_size=3)
        solver.solve(cost_mat)
        elite = solver.get_elite_pool()

        assert len(elite) <= 3, f"精英池应不超过 3 个: {len(elite)}"
        assert len(elite) >= 1, "精英池至少应有 1 个解"

    # ---------- 多起点 ----------
    def test_vns_multi_start_best_selected(self, n20_dataset):
        spots, cost_mat, _ = n20_dataset
        city_indices = list(range(1, len(spots)))

        solver = VNSSolver(city_indices, spots)
        res = solver.solve(cost_mat)

        assert res["best_solution"][0] == 0
        assert res["best_solution"][-1] == 0
        assert res["best_cost"] > 0

    # ---------- 收敛 ----------
    def test_vns_convergence(self, n20_dataset):
        spots, cost_mat, _ = n20_dataset
        city_indices = list(range(1, len(spots)))

        solver = VNSSolver(city_indices, spots)
        res = solver.solve(cost_mat)

        conv = res["convergence_history"]
        assert len(conv) >= 2, "应有收敛历史"
        for i in range(1, len(conv)):
            assert conv[i] <= conv[i - 1] + 1e-6, "收敛历史不应上升"

    def test_vns_with_initial_solution(self, n20_dataset):
        spots, cost_mat, _ = n20_dataset
        city_indices = list(range(1, len(spots)))

        ca = CASolver(city_indices, spots)
        ca_res = ca.solve(cost_mat)

        vns = VNSSolver(city_indices, spots)
        vns_res = vns.solve(cost_mat, initial_solution=ca_res["best_solution"])

        visited = set(vns_res["best_solution"][1:-1])
        assert visited == set(city_indices), "初始化解后应覆盖所有节点"
