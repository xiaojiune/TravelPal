# src/engine/ca.py

import math
import random
import numpy as np
from numba import njit

# ================== CA 默认参数 ==================
# ***** 压缩退火参数（正确版本）*****
# 说明：压缩退火通过动态调整接受准则中惩罚项的权重来实现
# 初期 compressed_penalty_start 很小 → 对惩罚增加不敏感，允许探索不可行区域
# 后期逐渐增大到 compressed_penalty_end → 与原始成本一致，强制收敛到可行解
CA_DEFAULT_PARAMS = {
    'max_iter': 2000,
    'initial_temperature': 1000.0,
    'cooling_rate': 0.95,
    'min_temperature': 1e-8,
    'inner_iter': 10,
    'use_time_window_guided': True,
    'use_compressed_annealing': True,
    'compressed_penalty_start': 0.1,
    'compressed_penalty_end': 1.0,
    'min_clusters': 1,
    'max_clusters': 10,
    'early_stop_gain_threshold': 1.0,
    'stop_consecutive_worse': 3,
}

# ================== Numba 适应度内核 ==================

@njit(cache=True)
def _cal_fitness_numba(line, dis_matrix, travel_speed, penalty_weight,
                       early_wait_weight, late_return_weight, depot_index,
                       spots_start, spots_end, spots_stay):
    """Numba JIT 编译的适应度计算内核（与 VNS 共享相同逻辑）"""
    if len(line) < 3:
        return 999999.0, 999999.0, 999999.0

    dis_sum = 0.0
    time_penalty = 0.0
    depot_start = spots_start[depot_index]
    depot_end = spots_end[depot_index]
    current_time = depot_start

    for i in range(len(line) - 1):
        fr = line[i]
        to = line[i + 1]
        d = dis_matrix[fr][to]
        dis_sum += d
        travel_time = d / travel_speed
        arrival = current_time + travel_time

        if to != depot_index:
            start_t = spots_start[to]
            end_t = spots_end[to]
            stay = spots_stay[to]

            if arrival < start_t:
                wait = start_t - arrival
                time_penalty += wait * early_wait_weight
                current_time = start_t + stay
            elif arrival > end_t:
                late = arrival - end_t
                time_penalty += late * penalty_weight
                current_time = arrival + stay
            else:
                current_time = arrival + stay
        else:
            if arrival > depot_end:
                time_penalty += (arrival - depot_end) * late_return_weight
            current_time = arrival

    if current_time > depot_end:
        time_penalty += (current_time - depot_end) * late_return_weight

    total = dis_sum + time_penalty
    return round(total, 1), round(dis_sum, 1), round(time_penalty, 1)


# ================== CASolver 主类 ==================

class CASolver:
    """
    压缩退火求解器（Compressed Annealing）。

    基于模拟退火框架，引入压缩系数动态调节距离成本与时间惩罚之间的权重比例。
    搜索初期偏向探索可行域之外的区域，后期逐渐收紧至可行解。
    """

    def __init__(self, city_indices, spots_dict, travel_speed=1.0,
                 penalty_weight=100.0, early_wait_weight=0.1,
                 late_return_weight=50.0, depot_index=0, **kwargs):
        """
        初始化压缩退火求解器。

        Args:
            city_indices: 需要规划路径的城市索引列表。
            spots_dict: 景点字典，每项含 {"tw": (start, end), "stay": float}。
            travel_speed: 旅行速度（距离/时间单位）。
            penalty_weight: 迟到惩罚权重。
            early_wait_weight: 早到等待惩罚权重。
            late_return_weight: 晚归惩罚权重。
            depot_index: 起终点索引（默认为 0）。
            **kwargs: 覆盖 CA_DEFAULT_PARAMS 的额外参数。
        """
        self.city_indices = list(city_indices)
        self.num_cities = len(city_indices)
        self.spots_dict = spots_dict
        self.travel_speed = travel_speed
        self.penalty_weight = penalty_weight
        self.early_wait_weight = early_wait_weight
        self.late_return_weight = late_return_weight
        self.depot_index = depot_index

        self.params = CA_DEFAULT_PARAMS.copy()
        self.params.update(kwargs)

        # Numba 预提取数组
        n = len(spots_dict)
        self.spots_start = np.array([spots_dict[i]["tw"][0] for i in range(n)], dtype=np.float64)
        self.spots_end = np.array([spots_dict[i]["tw"][1] for i in range(n)], dtype=np.float64)
        self.spots_stay = np.array([spots_dict[i]["stay"] for i in range(n)], dtype=np.float64)

    # ---------- 适应度计算 ----------

    def _cal_fitness(self, line, dis_matrix):
        """直接调用 Numba 内核（无需缓存，CA 单次运行不重复评估同一解）"""
        line_arr = np.array(line, dtype=np.int32)
        dis_arr = np.asarray(dis_matrix, dtype=np.float64)
        return _cal_fitness_numba(
            line_arr, dis_arr,
            self.travel_speed, self.penalty_weight,
            self.early_wait_weight, self.late_return_weight,
            self.depot_index,
            self.spots_start, self.spots_end, self.spots_stay
        )

    # ---------- 初始解 ----------

    def _initial_solution(self):
        """按时间窗起始时间排序生成初始解（启发式效果优于随机）"""
        if self.num_cities > 0:
            cities_with_time = [(c, self.spots_dict[c]["tw"][0]) for c in self.city_indices]
            cities_with_time.sort(key=lambda x: x[1])
            return [self.depot_index] + [c for c, _ in cities_with_time] + [self.depot_index]
        return [self.depot_index, self.depot_index]

    # ---------- 标准邻域生成 ----------

    def _standard_neighbor(self, solution, temp_ratio):
        """
        标准邻域生成器。

        根据当前退火温度比例选择不同类型的变异：
        - 高温段（temp_ratio > 0.7）：大范围反转
        - 中温段（temp_ratio > 0.3）：交换两点
        - 低温段：插入操作（精细化微调）
        """
        neighbor = solution.copy()
        inner = neighbor[1:-1]
        if len(inner) < 2:
            return neighbor
        if temp_ratio > 0.7 or random.random() < temp_ratio:
            # 大范围反转
            i = random.randint(0, len(inner) - 2)
            j = random.randint(i + 1, len(inner) - 1)
            inner[i:j + 1] = reversed(inner[i:j + 1])
        elif temp_ratio > 0.3 or random.random() < 0.5:
            # 交换两点
            i, j = random.sample(range(len(inner)), 2)
            inner[i], inner[j] = inner[j], inner[i]
        else:
            # 插入重定位
            i = random.randint(0, len(inner) - 1)
            j = random.randint(0, len(inner) - 1)
            while i == j:
                j = random.randint(0, len(inner) - 1)
            city = inner.pop(i)
            inner.insert(j, city)
        neighbor[1:-1] = inner
        return neighbor

    # ---------- 时间窗引导邻域 ----------

    def _time_window_guided_neighbor(self, solution, dis_matrix, temp_ratio):
        """
        时间窗引导邻域生成。

        识别违反时间窗最严重的节点，将其重定位到路径中另一随机位置。
        适用于搜索早期快速修正不可行解。
        """
        if len(solution) <= 4:
            return solution.copy()
        violations = {}
        depot_start = self.spots_dict[self.depot_index]["tw"][0]
        current_time = depot_start
        for i in range(len(solution) - 1):
            fr, to = solution[i], solution[i + 1]
            dis = dis_matrix[fr][to]
            arrival = current_time + dis / self.travel_speed
            if to != self.depot_index:
                spot = self.spots_dict[to]
                if arrival < spot["tw"][0]:
                    violations[to] = (spot["tw"][0] - arrival) * self.early_wait_weight
                elif arrival > spot["tw"][1]:
                    violations[to] = (arrival - spot["tw"][1]) * self.penalty_weight
                else:
                    violations[to] = 0
                current_time = max(arrival, spot["tw"][0])
            else:
                current_time = arrival
        if not violations:
            return self._standard_neighbor(solution, temp_ratio)
        # 找到违规最严重的节点并重定位
        max_node = max(violations, key=violations.get)
        idx = solution.index(max_node) if max_node in solution else -1
        if idx <= 0 or idx >= len(solution) - 1:
            return self._standard_neighbor(solution, temp_ratio)
        inner = solution[1:-1]
        viol_idx = idx - 1
        new_pos = random.randint(0, len(inner) - 1)
        while new_pos == viol_idx:
            new_pos = random.randint(0, len(inner) - 1)
        city = inner.pop(viol_idx)
        inner.insert(new_pos, city)
        return [self.depot_index] + inner + [self.depot_index]

    def _get_neighbor(self, solution, iteration, max_iter, dis_matrix):
        """混合邻域选择：50% 概率使用时间窗引导，50% 使用标准邻域"""
        temp_ratio = iteration / max_iter if max_iter > 0 else 0.5
        if self.params['use_time_window_guided'] and random.random() < 0.5:
            return self._time_window_guided_neighbor(solution, dis_matrix, temp_ratio)
        return self._standard_neighbor(solution, temp_ratio)

    # ---------- 2-opt 局部搜索 ----------

    def _local_search_2opt(self, solution, dis_matrix, max_iter=20):
        """
        2-opt 局部搜索（First Improvement）。

        遍历所有可能的反转对，找到改善立即应用并重新扫描。
        """
        best_sol = solution.copy()
        best_cost, _, _ = self._cal_fitness(best_sol, dis_matrix)
        improved = True
        it = 0
        while improved and it < max_iter:
            improved = False
            inner = best_sol[1:-1]
            for i in range(len(inner) - 1):
                for j in range(i + 2, len(inner)):
                    new_inner = inner.copy()
                    new_inner[i:j + 1] = reversed(new_inner[i:j + 1])
                    new_sol = [self.depot_index] + new_inner + [self.depot_index]
                    new_cost, _, _ = self._cal_fitness(new_sol, dis_matrix)
                    if new_cost < best_cost:
                        best_sol, best_cost = new_sol, new_cost
                        improved = True
                        break
                if improved:
                    break
            it += 1
        return best_sol

    # ---------- 主求解入口 ----------

    def solve(self, dis_matrix):
        """
        执行压缩退火主循环。

        Args:
            dis_matrix: 距离矩阵。

        Returns:
            dict: {'best_solution', 'best_cost', 'best_distance', 'best_penalty', 'convergence_history'}
        """
        cur = self._initial_solution()
        cur_cost, cur_dist, cur_pen = self._cal_fitness(cur, dis_matrix)
        best_sol = cur.copy()
        best_cost, best_dist, best_pen = cur_cost, cur_dist, cur_pen
        conv = [best_cost]

        temp = self.params['initial_temperature']
        iteration = 0
        max_iter = self.params['max_iter']
        use_comp = self.params['use_compressed_annealing']
        start_compress = self.params['compressed_penalty_start']
        end_compress = self.params['compressed_penalty_end']

        while temp > self.params['min_temperature'] and iteration < max_iter:
            # 压缩系数（随迭代进度线性增长）
            if use_comp:
                progress = iteration / max_iter if max_iter > 0 else 0.0
                compress_factor = start_compress + (end_compress - start_compress) * progress
            else:
                compress_factor = 1.0

            for _ in range(self.params['inner_iter']):
                neighbor = self._get_neighbor(cur, iteration, max_iter, dis_matrix)
                n_cost, n_dist, n_pen = self._cal_fitness(neighbor, dis_matrix)

                if use_comp:
                    # 压缩退火接受准则：距离差 + 压缩系数 × 惩罚差
                    delta = (n_dist - cur_dist) + compress_factor * (n_pen - cur_pen)
                else:
                    delta = n_cost - cur_cost

                # Metropolis 接收准则
                if delta < 0 or (temp > 0 and random.random() < math.exp(-delta / temp)):
                    cur = neighbor
                    cur_cost, cur_dist, cur_pen = n_cost, n_dist, n_pen

                    if cur_cost < best_cost:
                        best_sol = cur.copy()
                        best_cost, best_dist, best_pen = cur_cost, cur_dist, cur_pen

            conv.append(best_cost)
            temp *= self.params['cooling_rate']
            iteration += 1

        # 最终 2-opt 精细化
        if best_sol:
            refined = self._local_search_2opt(best_sol, dis_matrix, max_iter=30)
            r_cost, r_dist, r_pen = self._cal_fitness(refined, dis_matrix)
            if r_cost < best_cost:
                best_sol, best_cost, best_dist, best_pen = refined, r_cost, r_dist, r_pen

        return {
            'best_solution': best_sol,
            'best_cost': best_cost,
            'best_distance': best_dist,
            'best_penalty': best_pen,
            'convergence_history': conv
        }
