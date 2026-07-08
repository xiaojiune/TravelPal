import pytest
import numpy as np
from tests.dataset_loader import load_tsptw_dataset, find_dataset

# 数据集 fixture 覆盖四种规模：n20（小）、n60（中）、n100（中大）、n200（大）


@pytest.fixture(scope="session")
def n20_dataset() -> tuple[dict, np.ndarray, int]:
    return load_tsptw_dataset(find_dataset("n20w20", 1))


@pytest.fixture(scope="session")
def n60_dataset() -> tuple[dict, np.ndarray, int]:
    return load_tsptw_dataset(find_dataset("n60w60", 3))


@pytest.fixture(scope="session")
def n100_dataset() -> tuple[dict, np.ndarray, int]:
    return load_tsptw_dataset(find_dataset("n100w20", 1))


@pytest.fixture(scope="session")
def n200_dataset() -> tuple[dict, np.ndarray, int]:
    return load_tsptw_dataset(find_dataset("n200w40", 5))


DATASET_IDS = [
    "n20w20.001",
    "n60w60.003",
    "n100w20.001",
    "n200w40.005",
]


def _load(subdir: str, instance: int) -> tuple[dict, np.ndarray, int]:
    """按子目录和编号加载数据集，供 any_dataset 参数化 fixture 调用。"""
    return load_tsptw_dataset(find_dataset(subdir, instance))


@pytest.fixture(params=[
    ("n20w20", 1),
    ("n60w60", 3),
    ("n100w20", 1),
    ("n200w40", 5),
], ids=DATASET_IDS)

# ================== 内部函数 ==================
def any_dataset(request: pytest.FixtureRequest) -> tuple[dict, np.ndarray, int]:
    subdir, instance = request.param
    return _load(subdir, instance)
