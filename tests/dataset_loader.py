import os

import numpy as np
from sklearn.manifold import MDS


def load_tsptw_dataset(filepath: str) -> tuple[dict, np.ndarray, int]:
    """
    加载 TSPTW 标准格式数据集。

    格式说明：首行为景点数 n，接下来 n 行为 n×n 距离矩阵，
    再 n 行为每个景点的时间窗 (start, end)。
    最终通过 MDS 将距离矩阵降维到二维坐标用于可视化。

    Args:
        filepath: 数据集文件路径。

    Returns:
        Tuple[dict, np.ndarray, int]: (spots字典, 距离矩阵, 景点数n)。
    """
    with open(filepath) as f:
        lines = f.readlines()

    n = int(lines[0].strip())
    cost_mat = np.array([
        list(map(int, lines[i + 1].strip().split()))
        for i in range(n)
    ], dtype=np.float64)

    time_windows = []
    for i in range(n + 1, 2 * n + 1):
        parts = lines[i].strip().split()
        tw = (float(parts[0]), float(parts[1]))
        time_windows.append(tw)

    coords = _compute_mds_coords(cost_mat)

    basename = os.path.splitext(os.path.basename(filepath))[0]
    spots = {}
    for i in range(n):
        spots[i] = {
            "name": f"{basename}-{i}",
            "tw": time_windows[i],
            "stay": 0,
            "x": coords[i, 0],
            "y": coords[i, 1],
        }

    return spots, cost_mat, n


# ================== MDS 降维 ==================


def _compute_mds_coords(cost_mat: np.ndarray) -> np.ndarray:
    """通过 MDS 将距离矩阵降维为二维坐标，用于景点位置展示"""
    mds = MDS(
        n_components=2,
        metric=True,
        dissimilarity="precomputed",
        random_state=42,
        n_init=4,
        normalized_stress=False,
        max_iter=1000,
    )
    return mds.fit_transform(cost_mat)


# ================== 数据集路径查找 ==================


def find_dataset(subdir: str, instance: int = 1) -> str:
    """在 data/datasets/ 下查找指定编号的数据集文件

    Args:
        subdir: 数据集子目录名（如 "n20w20"）。
        instance: 实例编号，默认 1。

    Returns:
        str: 数据集绝对路径。

    Raises:
        FileNotFoundError: 数据集文件不存在。
    """
    base = os.path.join(os.path.dirname(__file__), "..", "raw_data", "DataSets")
    path = os.path.join(base, subdir, f"{subdir}.{instance:03d}.txt")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Dataset not found: {path}")
    return os.path.abspath(path)
