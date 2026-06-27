import os
import numpy as np
from sklearn.manifold import MDS


def load_tsptw_dataset(filepath: str) -> tuple[dict, np.ndarray, int]:
    with open(filepath) as f:
        lines = f.readlines()

    n = int(lines[0].strip())
    dist_mat = np.array([
        list(map(int, lines[i + 1].strip().split()))
        for i in range(n)
    ], dtype=np.float64)

    time_windows = []
    for i in range(n + 1, 2 * n + 1):
        parts = lines[i].strip().split()
        tw = (float(parts[0]), float(parts[1]))
        time_windows.append(tw)

    coords = _compute_mds_coords(dist_mat)

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

    return spots, dist_mat, n


def _compute_mds_coords(dist_mat: np.ndarray) -> np.ndarray:
    mds = MDS(
        n_components=2,
        metric=True,
        dissimilarity="precomputed",
        random_state=42,
        n_init=4,
        normalized_stress=False,
        max_iter=1000,
    )
    return mds.fit_transform(dist_mat)


def find_dataset(subdir: str, instance: int = 1) -> str:
    base = os.path.join(os.path.dirname(__file__), "..", "data", "datasets")
    path = os.path.join(base, subdir, f"{subdir}.{instance:03d}.txt")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Dataset not found: {path}")
    return os.path.abspath(path)
