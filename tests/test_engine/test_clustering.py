import numpy as np
import pytest
from src.engine.clustering import CLUSTER_METHODS, call_cluster


class TestClustering:
    """6 种聚类方法的正确性与分组覆盖验证"""

    def test_all_methods_return_valid_groups(self, n20_dataset):
        spots, dist_mat, _ = n20_dataset
        depot = 0
        k = 3
        spot_ids = set(spots.keys()) - {depot}

        for full_name, method_func in CLUSTER_METHODS:
            groups = call_cluster(method_func, spots, depot, k, dist_mat)

            assert len(groups) == k, f"{full_name}: 组数={len(groups)}, 应为 {k}"

            all_assigned = set()
            for g in groups:
                for node in g:
                    assert isinstance(node, (int, np.integer)), f"{full_name}: 节点 {node} 类型错误"
                    all_assigned.add(node)

            assert all_assigned == spot_ids, (
                f"{full_name}: 遗漏节点 {spot_ids - all_assigned}, "
                f"多余节点 {all_assigned - spot_ids}"
            )

    def test_cluster_count_matches_k(self, any_dataset):
        # 参数化验证（any_dataset 覆盖 n20/n60/n100/n200 四种规模），确保每种方法都精确返回 k 组
        spots, dist_mat, _ = any_dataset
        depot = 0

        for k in range(2, min(6, len(spots))):
            for full_name, method_func in CLUSTER_METHODS:
                groups = call_cluster(method_func, spots, depot, k, dist_mat)
                assert len(groups) == k, (
                    f"{full_name}: k={k}, 实际组数={len(groups)}"
                )

    def test_each_group_nonempty(self, n20_dataset):
        spots, dist_mat, _ = n20_dataset
        depot = 0

        for full_name, method_func in CLUSTER_METHODS:
            groups = call_cluster(method_func, spots, depot, 4, dist_mat)
            for idx, g in enumerate(groups):
                assert len(g) > 0, f"{full_name}: 第 {idx} 组为空"

    def test_different_k_produce_different_partitions(self, n20_dataset):
        spots, dist_mat, _ = n20_dataset
        depot = 0
        _, method_func = CLUSTER_METHODS[0]

        groups_k2 = call_cluster(method_func, spots, depot, 2, dist_mat)
        groups_k3 = call_cluster(method_func, spots, depot, 3, dist_mat)

        flat_k2 = sorted(node for g in groups_k2 for node in g)
        flat_k3 = sorted(node for g in groups_k3 for node in g)
        assert flat_k2 == flat_k3, "不同 k 值应覆盖相同节点集"
