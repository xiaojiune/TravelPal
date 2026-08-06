import numpy as np
import pytest

from tests.dataset_loader import find_dataset, load_tsptw_dataset

# 数据集 fixture 覆盖五种规模：n20（小）、n40（中）、n60（中偏大）、n80（大）、n100（大）
# 统一取 w20 最窄时间窗（n60 保持 w60 宽窗既有实例），对聚类/求解的时间窗约束更具区分度


@pytest.fixture(scope="session")
def n20_dataset() -> tuple[dict, np.ndarray, int]:
    return load_tsptw_dataset(find_dataset("n20w20", 1))


@pytest.fixture(scope="session")
def n40_dataset() -> tuple[dict, np.ndarray, int]:
    return load_tsptw_dataset(find_dataset("n40w20", 1))


@pytest.fixture(scope="session")
def n60_dataset() -> tuple[dict, np.ndarray, int]:
    return load_tsptw_dataset(find_dataset("n60w60", 3))


@pytest.fixture(scope="session")
def n80_dataset() -> tuple[dict, np.ndarray, int]:
    return load_tsptw_dataset(find_dataset("n80w20", 1))


@pytest.fixture(scope="session")
def n100_dataset() -> tuple[dict, np.ndarray, int]:
    return load_tsptw_dataset(find_dataset("n100w20", 1))


DATASET_IDS = [
    "n20w20.001",
    "n40w20.001",
    "n60w60.003",
    "n80w20.001",
    "n100w20.001",
]


def _load(subdir: str, instance: int) -> tuple[dict, np.ndarray, int]:
    """按子目录和编号加载数据集，供 any_dataset 参数化 fixture 调用。"""
    return load_tsptw_dataset(find_dataset(subdir, instance))


@pytest.fixture(
    params=[
        ("n20w20", 1),
        ("n40w20", 1),
        ("n60w60", 3),
        ("n80w20", 1),
        ("n100w20", 1),
    ],
    ids=DATASET_IDS,
)

# ================== 内部函数 ==================
def any_dataset(request: pytest.FixtureRequest) -> tuple[dict, np.ndarray, int]:
    subdir, instance = request.param
    return _load(subdir, instance)


@pytest.fixture(scope="session")
def base_adjust_plan(n20_dataset) -> tuple[dict, np.ndarray, list]:
    """基于 n20 数据集构建 2 天基准方案（spots/矩阵/routes），供方案调整测试复用。

    dataset_loader 的 spots 缺 original_tw（真实 run_planning 会构建该字段），
    这里补齐以适配 _rebuild_schedule 的访问。
    """
    from backend.engine.search import cluster_and_solve

    spots, cost_mat, _ = n20_dataset
    spots = {i: {**s, "original_tw": s["tw"]} for i, s in spots.items()}
    result = cluster_and_solve(spots, 0, cost_mat, mode="fast", n_days=2)
    assert result["type"] == "solution"
    return spots, cost_mat, result["solution"]["routes"]
