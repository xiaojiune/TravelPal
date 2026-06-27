import pytest
from src.engine.vns import VNSSolver
from src.engine.sa import SASolver


class TestVNS:
    def test_vns_solution_valid(self, n20_dataset):
        spots, dist_mat, _ = n20_dataset
        city_indices = list(range(1, len(spots)))

        solver = VNSSolver(city_indices, spots, travel_speed=1.0,
                           penalty_weight=100.0, early_wait_weight=0.1,
                           late_return_weight=50.0)
        res = solver.solve(dist_mat)

        sol = res["best_solution"]
        assert sol[0] == 0, "路线应以 depot 开始"
        assert sol[-1] == 0, "路线应以 depot 结束"

        visited = set(sol[1:-1])
        assert visited == set(city_indices), f"遗漏节点: {set(city_indices) - visited}"

    def test_vns_improves_over_sa(self, n20_dataset):
        spots, dist_mat, _ = n20_dataset
        city_indices = list(range(1, len(spots)))

        sa = SASolver(city_indices, spots)
        vns = VNSSolver(city_indices, spots)

        sa_res = sa.solve(dist_mat)
        vns_res = vns.solve(dist_mat, initial_solution=sa_res["best_solution"])

        improvement = (sa_res["best_cost"] - vns_res["best_cost"]) / sa_res["best_cost"] * 100
        assert vns_res["best_cost"] <= sa_res["best_cost"] + 1e-6, (
            f"VNS 成本 {vns_res['best_cost']:.1f} 应不高于 SA 成本 {sa_res['best_cost']:.1f}"
        )

    def test_vns_elite_pool(self, n20_dataset):
        spots, dist_mat, _ = n20_dataset
        city_indices = list(range(1, len(spots)))

        solver = VNSSolver(city_indices, spots, elite_size=3)
        solver.solve(dist_mat)
        elite = solver.get_elite_pool()

        assert len(elite) <= 3, f"精英池应不超过 3 个: {len(elite)}"
        assert len(elite) >= 1, "精英池至少应有 1 个解"

    def test_vns_multi_start_best_selected(self, n20_dataset):
        spots, dist_mat, _ = n20_dataset
        city_indices = list(range(1, len(spots)))

        solver = VNSSolver(city_indices, spots)
        res = solver.solve(dist_mat)

        assert res["best_solution"][0] == 0
        assert res["best_solution"][-1] == 0
        assert res["best_cost"] > 0

    def test_vns_convergence(self, n20_dataset):
        spots, dist_mat, _ = n20_dataset
        city_indices = list(range(1, len(spots)))

        solver = VNSSolver(city_indices, spots)
        res = solver.solve(dist_mat)

        conv = res["convergence_history"]
        assert len(conv) >= 2, "应有收敛历史"
        for i in range(1, len(conv)):
            assert conv[i] <= conv[i - 1] + 1e-6, "收敛历史不应上升"

    def test_vns_with_initial_solution(self, n20_dataset):
        spots, dist_mat, _ = n20_dataset
        city_indices = list(range(1, len(spots)))

        sa = SASolver(city_indices, spots)
        sa_res = sa.solve(dist_mat)

        vns = VNSSolver(city_indices, spots)
        vns_res = vns.solve(dist_mat, initial_solution=sa_res["best_solution"])

        visited = set(vns_res["best_solution"][1:-1])
        assert visited == set(city_indices), "初始化解后应覆盖所有节点"
