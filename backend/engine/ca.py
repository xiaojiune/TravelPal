"""压缩退火求解器（Compressed Annealing），基于模拟退火框架的 TSPTW 求解。"""

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
    "max_iter": 2000,
    "initial_temperature": 1000.0,
    "cooling_rate": 0.95,
    "min_temperature": 1e-8,
    "inner_iter": 10,
    "use_time_window_guided": True,
    "use_compressed_annealing": True,
    "compressed_penalty_start": 0.1,
    "compressed_penalty_end": 1.0,
    "early_stop_gain_threshold": 1.0,
    "stop_consecutive_worse": 3,
}

# ================== Numba 适应度内核 ==================


@njit(cache=True)
def _cal_fitness_numba(
    line,
    cost_mat,
    travel_speed,
    penalty_weight,
    early_wait_weight,
    late_return_weight,
    depot_index,
    spots_start,
    spots_end,
    spots_stay,
    use_real_time_matrix=False,
):
    """
    Numba JIT 编译的适应度计算内核（与 VNS 共享相同逻辑）。

    沿路径逐段模拟行程，累计总成本与时间惩罚。
    路径必须从 depot 出发并回到 depot，长度不足 3 时返回极大惩罚值。

    两种矩阵模式：
    - use_real_time_matrix=False（默认，标准数据集）：矩阵元素为距离，travel_time = d / travel_speed
    - use_real_time_matrix=True（高德真实数据）：矩阵元素为旅行时间（小时），travel_time = d

    Args:
        line: 路径数组（含起终点的完整路径）。
        cost_mat: 距离/旅行时间矩阵。
        travel_speed: 旅行速度（距离/时间单位）。use_real_time_matrix=True 时该参数无效。
        penalty_weight: 迟到惩罚权重。
        early_wait_weight: 早到等待惩罚权重。
        late_return_weight: 晚归惩罚权重。
        depot_index: 起终点索引。
        spots_start: 各景点时间窗开始时间数组。
        spots_end: 各景点时间窗结束时间数组。
        spots_stay: 各景点停留时长数组。
        use_real_time_matrix: 矩阵是否为旅行时间（避免 d / travel_speed 重复计算）。

    Returns:
        Tuple[float, float, float]: (总成本, 旅行累积值, 时间惩罚).
            旅行累积值：标准模式下为总距离，真实模式下为总旅行时间。
    """
    if len(line) < 3:
        return 999999.0, 999999.0, 999999.0

    travel_sum = 0.0
    time_penalty = 0.0
    depot_start = spots_start[depot_index]
    depot_end = spots_end[depot_index]
    current_time = depot_start

    for i in range(len(line) - 1):
        fr = line[i]
        to = line[i + 1]
        d = cost_mat[fr][to]
        travel_sum += d
        travel_time = d if use_real_time_matrix else d / travel_speed
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

    total = travel_sum + time_penalty
    return round(total, 1), round(travel_sum, 1), round(time_penalty, 1)


# ================== CASolver 主类 ==================


class CASolver:
    """
    压缩退火求解器（Compressed Annealing）。

    基于模拟退火框架，引入压缩系数动态调节距离成本与时间惩罚之间的权重比例。
    搜索初期偏向探索可行域之外的区域，后期逐渐收紧至可行解。

    增强特性：
    - 时间窗引导邻域：针对违规最严重的节点执行重定位扰动（加速不可行解修复）
    - 压缩系数动态增长：初期惩罚权重小（允许探索不可行区域），后期逐渐增大至与原始成本一致
    - 2-opt 精细化：主循环结束后对最优解执行 First Improvement 2-opt 局部搜索
    """

    def __init__(
        self,
        city_indices: list[int],
        spots_dict: dict,
        travel_speed: float = 1.0,
        penalty_weight: float = 100.0,
        early_wait_weight: float = 0.1,
        late_return_weight: float = 50.0,
        depot_index: int = 0,
        use_real_time_matrix: bool = False,
        **kwargs,
    ):
        """
        初始化压缩退火求解器。

        Args:
            city_indices: 需要规划路径的城市索引列表。
            spots_dict: 景点字典，每项含 {"tw": (start, end), "stay": float}。
            travel_speed: 旅行速度（距离/时间单位）。use_real_time_matrix=True 时无效。
            penalty_weight: 迟到惩罚权重。
            early_wait_weight: 早到等待惩罚权重。
            late_return_weight: 晚归惩罚权重。
            depot_index: 起终点索引（默认为 0）。
            use_real_time_matrix: 是否使用高德真实旅行时间矩阵。
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
        self.use_real_time_matrix = use_real_time_matrix

        self.params = CA_DEFAULT_PARAMS.copy()
        self.params.update(kwargs)

        # Numba 预提取数组
        n = len(spots_dict)
        self.spots_start = np.array([spots_dict[i]["tw"][0] for i in range(n)], dtype=np.float64)
        self.spots_end = np.array([spots_dict[i]["tw"][1] for i in range(n)], dtype=np.float64)
        self.spots_stay = np.array([spots_dict[i]["stay"] for i in range(n)], dtype=np.float64)

    # ---------- 适应度计算 ----------

    def _cal_fitness(self, line: list[int], cost_mat: np.ndarray):
        """直接调用 Numba 内核评估路径成本

        CA 单次运行中几乎不会重复评估同一解，故不设缓存。

        Args:
            line: 路径列表（含起终点的完整路径）。
            cost_mat: 距离/旅行时间矩阵。

        Returns:
            Tuple[float, float, float]: (总成本, 旅行累积值, 时间惩罚).
        """
        line_arr = np.array(line, dtype=np.int32)
        dis_arr = np.asarray(cost_mat, dtype=np.float64)
        return _cal_fitness_numba(
            line_arr,
            dis_arr,
            self.travel_speed,
            self.penalty_weight,
            self.early_wait_weight,
            self.late_return_weight,
            self.depot_index,
            self.spots_start,
            self.spots_end,
            self.spots_stay,
            self.use_real_time_matrix,
        )

    # ---------- 初始解 ----------

    def _initial_solution(self) -> list[int]:
        """按时间窗起始时间排序生成初始解（启发式效果优于随机）

        Returns:
            list[int]: 闭合路径 [depot, ...景点..., depot]。
        """
        if self.num_cities > 0:
            cities_with_time = [(c, self.spots_dict[c]["tw"][0]) for c in self.city_indices]
            cities_with_time.sort(key=lambda x: x[1])
            return [self.depot_index] + [c for c, _ in cities_with_time] + [self.depot_index]
        return [self.depot_index, self.depot_index]

    # ---------- 标准邻域生成 ----------

    def _standard_neighbor(self, solution: list[int], temp_ratio: float):
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
            # 高温段：大范围反转，强化全局探索能力
            i = random.randint(0, len(inner) - 2)
            j = random.randint(i + 1, len(inner) - 1)
            inner[i : j + 1] = reversed(inner[i : j + 1])
        elif temp_ratio > 0.3 or random.random() < 0.5:
            # 中温段：交换两点，平衡探索与利用
            i, j = random.sample(range(len(inner)), 2)
            inner[i], inner[j] = inner[j], inner[i]
        else:
            # 低温段：插入重定位，精细化微调局部结构
            i = random.randint(0, len(inner) - 1)
            j = random.randint(0, len(inner) - 1)
            while i == j:
                j = random.randint(0, len(inner) - 1)
            city = inner.pop(i)
            inner.insert(j, city)
        neighbor[1:-1] = inner
        return neighbor

    # ---------- 时间窗引导邻域 ----------

    def _time_window_guided_neighbor(self, solution: list[int], cost_mat: np.ndarray, temp_ratio: float):
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
            dis = cost_mat[fr][to]
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
        max_node = max(violations, key=violations.get)  # pyright: ignore[reportCallIssue, reportArgumentType]
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

    def _get_neighbor(self, solution: list[int], iteration: int, max_iter: int, cost_mat: np.ndarray):
        """混合邻域选择：50% 概率使用时间窗引导，50% 使用标准邻域

        Args:
            solution: 当前解路径。
            iteration: 当前迭代次数。
            max_iter: 总迭代次数。
            cost_mat: 距离矩阵。

        Returns:
            List[int]: 新邻居解路径。
        """
        temp_ratio = iteration / max_iter if max_iter > 0 else 0.5
        if self.params["use_time_window_guided"] and random.random() < 0.5:
            return self._time_window_guided_neighbor(solution, cost_mat, temp_ratio)
        return self._standard_neighbor(solution, temp_ratio)

    # ---------- 2-opt 局部搜索 ----------

    def _local_search_2opt(self, solution: list[int], cost_mat: np.ndarray, max_iter: int = 20):
        """
        2-opt 局部搜索（First Improvement）。

        使用 First Improvement 而非 Best Improvement 策略：
        找到首个改善即接受，牺牲单步最优性换取更快的整体收敛速度。
        """
        best_sol = solution.copy()
        best_cost, _, _ = self._cal_fitness(best_sol, cost_mat)
        improved = True
        it = 0
        while improved and it < max_iter:
            improved = False
            inner = best_sol[1:-1]
            for i in range(len(inner) - 1):
                for j in range(i + 2, len(inner)):
                    new_inner = inner.copy()
                    new_inner[i : j + 1] = reversed(new_inner[i : j + 1])
                    new_sol = [self.depot_index] + new_inner + [self.depot_index]
                    new_cost, _, _ = self._cal_fitness(new_sol, cost_mat)
                    if new_cost < best_cost:
                        best_sol, best_cost = new_sol, new_cost
                        improved = True
                        break
                if improved:
                    break
            it += 1
        return best_sol

    # ---------- 主求解入口 ----------

    def solve(self, cost_mat: np.ndarray):
        """
        执行压缩退火主循环。

        Args:
            cost_mat: 距离矩阵。

        Returns:
            dict: 包含以下键：
                - best_solution (List[int]): 最优路径（含起终点）。
                - best_cost (float): 最优总成本（旅行累积值 + 时间惩罚，单位由输入矩阵决定）。
                - best_distance (float): 旅行累积值。标准模式 = 总距离；真实模式 = 总旅行时间。
                - best_penalty (float): 最优路径总时间惩罚。
                - convergence_history (List[float]): 收敛曲线，每轮迭代后的最优成本。
        """
        cur = self._initial_solution()
        cur_cost, cur_dist, cur_pen = self._cal_fitness(cur, cost_mat)
        best_sol = cur.copy()
        best_cost, best_dist, best_pen = cur_cost, cur_dist, cur_pen
        conv = [best_cost]

        temp = self.params["initial_temperature"]
        iteration = 0
        max_iter = self.params["max_iter"]
        use_comp = self.params["use_compressed_annealing"]
        start_compress = self.params["compressed_penalty_start"]
        end_compress = self.params["compressed_penalty_end"]

        while temp > self.params["min_temperature"] and iteration < max_iter:
            # 压缩系数（随迭代进度线性增长）
            if use_comp:
                progress = iteration / max_iter if max_iter > 0 else 0.0
                compress_factor = start_compress + (end_compress - start_compress) * progress
            else:
                compress_factor = 1.0

            for _ in range(self.params["inner_iter"]):
                neighbor = self._get_neighbor(cur, iteration, max_iter, cost_mat)
                n_cost, n_dist, n_pen = self._cal_fitness(neighbor, cost_mat)

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
            temp *= self.params["cooling_rate"]
            iteration += 1

        # 最终 2-opt 精细化
        if best_sol:
            refined = self._local_search_2opt(best_sol, cost_mat, max_iter=30)
            r_cost, r_dist, r_pen = self._cal_fitness(refined, cost_mat)
            if r_cost < best_cost:
                best_sol, best_cost, best_dist, best_pen = refined, r_cost, r_dist, r_pen

        return {
            "best_solution": best_sol,
            "best_cost": best_cost,
            "best_distance": best_dist,
            "best_penalty": best_pen,
            "convergence_history": conv,
        }
