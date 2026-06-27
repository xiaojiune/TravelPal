import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


def cluster_by_distance_kmeans(spots, depot, n_clusters):
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
                    groups[i].remove(j_earliest)
                    groups[j].remove(i_latest)
                    groups[i].append(i_latest)
                    groups[j].append(j_earliest)
                else:
                    improved = True
        if not improved:
            break
    return groups


CLUSTER_METHODS = [
    ("1. 基于距离的K-means聚类", cluster_by_distance_kmeans),
    ("2. 基于时间窗的聚类", cluster_by_time_window),
    ("3. 基于时空特征的聚类", cluster_by_spatiotemporal),
    ("4. 基于时间窗重叠的启发式分组", cluster_by_time_overlap),
    ("5. 基于时间窗密度的聚类", cluster_by_time_density),
    ("6. 混合分组方法", cluster_hybrid_optimized)
]


def call_cluster(func, spots, depot, k, dist_mat=None):
    if func.__name__ == 'cluster_hybrid_optimized':
        return func(spots, dist_mat, depot, k)
    return func(spots, depot, k)


def pure_name(full_name):
    return full_name.split(". ", 1)[1] if ". " in full_name else full_name


def find_method_func(name):
    for full, func in CLUSTER_METHODS:
        if pure_name(full) == name or full == name:
            return func
    return None
