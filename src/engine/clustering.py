# src/engine/clustering.py

import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# ================== 聚类方法 ==================

def cluster_by_distance_kmeans(spots, depot, n_clusters):
    """
    基于地理坐标的 K-means 聚类。

    Args:
        spots: 景点字典，每项含 {"x": float, "y": float}。
        depot: depot 索引。
        n_clusters: 聚类组数。

    Returns:
        List[List[int]]: 每个分组包含的景点索引列表。
    """
    coords, indices = [], []
    for i, spot in spots.items():
        if i != depot:
            coords.append([spot["x"], spot["y"]])
            indices.append(i)
    if not coords:
        return [[] for _ in range(n_clusters)]
    labels = KMeans(n_clusters=n_clusters, random_state=42, n_init=10).fit_predict(np.array(coords))
    groups = [[] for _ in range(n_clusters)]
    for idx, lab in zip(indices, labels):
        groups[lab].append(idx)
    return groups


def cluster_by_time_window(spots, depot, n_clusters):
    """
    基于时间窗特征的 K-means 聚类。

    特征向量：[开放时间, 关闭时间, 时间窗跨度]。
    适用于将营业时间相似的景点分到同一天。

    Args:
        spots: 景点字典。
        depot: depot 索引。
        n_clusters: 聚类组数。

    Returns:
        List[List[int]]: 每个分组包含的景点索引列表。
    """
    features, indices = [], []
    for i, spot in spots.items():
        if i != depot:
            start, end = spot["tw"]
            features.append([start, end, end - start])
            indices.append(i)
    if not features:
        return [[] for _ in range(n_clusters)]
    labels = KMeans(n_clusters=n_clusters, random_state=42, n_init=10).fit_predict(np.array(features))
    groups = [[] for _ in range(n_clusters)]
    for idx, lab in zip(indices, labels):
        groups[lab].append(idx)
    return groups


def cluster_by_spatiotemporal(spots, depot, n_clusters, sp_w=0.5, tp_w=0.5):
    """
    时空联合聚类（距离 + 时间窗）。

    将坐标和时间窗拼接为四维特征，通过权重参数调节空间与时间的相对重要性。

    Args:
        spots: 景点字典。
        depot: depot 索引。
        n_clusters: 聚类组数。
        sp_w: 空间权重（默认 0.5）。
        tp_w: 时间权重（默认 0.5）。

    Returns:
        List[List[int]]: 每个分组包含的景点索引列表。
    """
    features, indices = [], []
    for i, spot in spots.items():
        if i != depot:
            features.append([spot["x"], spot["y"], spot["tw"][0], spot["tw"][1]])
            indices.append(i)
    if not features:
        return [[] for _ in range(n_clusters)]
    scaled = StandardScaler().fit_transform(np.array(features))
    scaled[:, 0:2] *= sp_w
    scaled[:, 2:4] *= tp_w
    labels = KMeans(n_clusters=n_clusters, random_state=42, n_init=10).fit_predict(scaled)
    groups = [[] for _ in range(n_clusters)]
    for idx, lab in zip(indices, labels):
        groups[lab].append(idx)
    return groups


def cluster_by_time_overlap(spots, depot, n_clusters):
    """
    时间窗重叠启发式分组。

    将景点按时间窗起始时间排序后平摊到各组，保证每组时间窗连续。
    无随机性，结果确定。

    Args:
        spots: 景点字典。
        depot: depot 索引。
        n_clusters: 聚类组数。

    Returns:
        List[List[int]]: 每个分组包含的景点索引列表。
    """
    cities = []
    for i, spot in spots.items():
        if i != depot:
            cities.append({'id': i, 'start': spot["tw"][0], 'end': spot["tw"][1]})
    if not cities:
        return [[] for _ in range(n_clusters)]
    cities.sort(key=lambda x: x['start'])
    groups = [[] for _ in range(n_clusters)]
    base = len(cities) // n_clusters
    rem = len(cities) % n_clusters
    idx = 0
    for g in range(n_clusters):
        sz = base + (1 if g < rem else 0)
        for _ in range(sz):
            groups[g].append(cities[idx]['id'])
            idx += 1
    return groups


def cluster_by_time_density(spots, depot, n_clusters):
    """
    基于时间窗密度的 K-means 聚类。

    仅使用时间窗起始时间作为一维特征，适用于时间段高度聚集的场景。

    Args:
        spots: 景点字典。
        depot: depot 索引。
        n_clusters: 聚类组数。

    Returns:
        List[List[int]]: 每个分组包含的景点索引列表。
    """
    times, indices = [], []
    for i, spot in spots.items():
        if i != depot:
            times.append([spot["tw"][0]])
            indices.append(i)
    if not times:
        return [[] for _ in range(n_clusters)]
    labels = KMeans(n_clusters=n_clusters, random_state=42, n_init=10).fit_predict(np.array(times))
    groups = [[] for _ in range(n_clusters)]
    for idx, lab in zip(indices, labels):
        groups[lab].append(idx)
    return groups


def cluster_hybrid_optimized(spots, dist_mat, depot, n_clusters):
    """
    混合优化分组（时间窗排序 + 距离优化重分配）。

    先按时间窗排序平摊，再通过交换分组间边界节点来优化组内距离。
    迭代至多 10 轮，无改善则提前停止。

    Args:
        spots: 景点字典。
        dist_mat: 距离矩阵，用于评估交换收益。
        depot: depot 索引。
        n_clusters: 聚类组数。

    Returns:
        List[List[int]]: 每个分组包含的景点索引列表。
    """
    cities = []
    for i, spot in spots.items():
        if i != depot:
            cities.append({'id': i, 'start': spot["tw"][0], 'end': spot["tw"][1]})
    if not cities:
        return [[] for _ in range(n_clusters)]
    cities.sort(key=lambda x: x['start'])
    groups = [[] for _ in range(n_clusters)]
    base = len(cities) // n_clusters
    rem = len(cities) % n_clusters
    idx = 0
    for g in range(n_clusters):
        sz = base + (1 if g < rem else 0)
        for _ in range(sz):
            groups[g].append(cities[idx]['id'])
            idx += 1
    # 交换优化：将各组最晚节点与下一组最早节点交换以降低组内距离
    for _ in range(10):
        improved = False
        for i in range(n_clusters - 1):
            for j in range(i + 1, n_clusters):
                if not groups[i] or not groups[j]:
                    continue
                i_latest = max(groups[i], key=lambda x: spots[x]["tw"][1])
                j_earliest = min(groups[j], key=lambda x: spots[x]["tw"][0])

                def avg_dist(g):
                    s = 0
                    cnt = 0
                    for a in g:
                        for b in g:
                            if a != b:
                                s += dist_mat[a][b]
                                cnt += 1
                    return s / max(1, cnt)

                before = avg_dist(groups[i]) + avg_dist(groups[j])
                groups[i].remove(i_latest)
                groups[j].remove(j_earliest)
                groups[i].append(j_earliest)
                groups[j].append(i_latest)
                after = avg_dist(groups[i]) + avg_dist(groups[j])
                if after > before:
                    # 交换后变差，撤销
                    groups[i].remove(j_earliest)
                    groups[j].remove(i_latest)
                    groups[i].append(i_latest)
                    groups[j].append(j_earliest)
                else:
                    improved = True
        if not improved:
            break
    return groups


# ================== 方法注册表与辅助函数 ==================

CLUSTER_METHODS = [
    ("1. 基于距离的K-means聚类", cluster_by_distance_kmeans),
    ("2. 基于时间窗的聚类", cluster_by_time_window),
    ("3. 基于时空特征的聚类", cluster_by_spatiotemporal),
    ("4. 基于时间窗重叠的启发式分组", cluster_by_time_overlap),
    ("5. 基于时间窗密度的聚类", cluster_by_time_density),
    ("6. 混合分组方法", cluster_hybrid_optimized)
]


def call_cluster(func, spots, depot, k, dist_mat=None):
    """
    统一调用聚类方法。

    cluster_hybrid_optimized 需要 dist_mat 参数，其余仅需 spots/depot/k。
    """
    if func.__name__ == 'cluster_hybrid_optimized':
        return func(spots, dist_mat, depot, k)
    return func(spots, depot, k)


def pure_name(full_name):
    """从带编号的全称中提取纯方法名，如 '1. xxx' → 'xxx'

    Returns:
        str: 纯方法名（去掉前缀编号）。
    """
    return full_name.split(". ", 1)[1] if ". " in full_name else full_name


def find_method_func(name):
    """通过方法名查找对应的函数对象

    Args:
        name: 方法名（带编号或不带均可）。

    Returns:
        callable | None: 找到的函数对象，未找到返回 None。
    """
    for full, func in CLUSTER_METHODS:
        if pure_name(full) == name or full == name:
            return func
    return None
