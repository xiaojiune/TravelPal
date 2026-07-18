"""变邻域搜索求解器（VNS），集成多种邻域算子和自适应权重机制。"""

import random
import math
from typing import Tuple, List
import numpy as np
from backend.typedefs import SpotDict
from numba import njit
from backend.engine.fitness import analyze_solution

# ================== VNS 默认参数 ==================
# VNS_DEFAULT_PARAMS 设计说明：
# - max_iter：主循环迭代次数，决定搜索深度，建议 100-300。
# - shaking_neighbors：抖动强度候选集合，数值越大扰动越剧烈。
# - local_search_iter：局部搜索迭代上限（当前未使用，保留扩展）。
# - no_improve_limit：连续无改善阈值，控制早停敏感度。
# - sa_initial_temp / sa_cooling_rate：SA 接收准则的退火速度与冷却率。
# - elite_size：精英池容量，保留历史上最优解结构。
# - final_vnd_rounds：主循环结束后对精英解额外进行 VND，提升最终解稳定性。
VNS_DEFAULT_PARAMS = {
    'max_iter': 200,
    'shaking_neighbors': [1, 2, 3],
    'local_search_iter': 50,
    'no_improve_limit': 30,
    'sa_initial_temp': 100.0,
    'sa_cooling_rate': 0.99,
    'elite_size': 3,
    'final_vnd_rounds': 2,
}

# ================== VNS 算法常量 ==================
# 这些常量控制抖动与自适应逻辑的行为，调参时可调整
# EARLY_EXPLORE_RATIO：经验值，0.3 表示前 30% 迭代为早期探索，调大则探索更充分但收敛变慢
# VIOLATOR_TARGET_PROB：经验值，定向扰动概率，过高易丢失优质解结构，过低则早期退化为随机搜索
# DYNAMIC_STRENGTHEN_AFTER：经验值，连续无改善次数阈值，过小导致抖动频繁震荡，过大则早停反应迟钝
# WEIGHT_REWARD_FACTOR：经验值，倍率过大导致权重快速倾斜（算子多样性下降），过小则自适应效果微弱
EARLY_EXPLORE_RATIO = 0.3
VIOLATOR_TARGET_PROB = 0.6
DYNAMIC_STRENGTHEN_AFTER = 10
WEIGHT_REWARD_FACTOR = 1.02

# ================== Numba 适应度内核 ==================

@njit(cache=True)
def _cal_fitness_numba(line: np.ndarray, cost_mat: np.ndarray, travel_speed: float,
                       penalty_weight: float, early_wait_weight: float,
                       late_return_weight: float, depot_index: int,
                       spots_start: np.ndarray, spots_end: np.ndarray,
                       spots_stay: np.ndarray,
                       use_real_time_matrix: bool = False) -> Tuple[float, float, float]:
    """
    Numba JIT 编译的适应度计算内核。

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
                # 早到 → 等待，按等待时长计惩罚
                wait = start_t - arrival
                time_penalty += wait * early_wait_weight
                current_time = start_t + stay
            elif arrival > end_t:
                # 迟到 → 超时惩罚（权重高）
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


# ================== VNSSolver 主类 ==================

class VNSSolver:
    """
    变邻域搜索求解器（Variable Neighborhood Search）。

    集成多种邻域结构（swap/inversion/insert/2opt）与 VND 局部搜索，
    通过 SA 准则控制扰动接受，并维护精英池保留历史最优解。

    增强特性：
    - SA 混合接受准则：改善解直接接受，劣化解按概率接受（避免陷入局部最优）
    - 早期定向约束扰动：迭代前期针对违规时间窗的节点执行针对性扰动（加速可行解发现）
    - 自适应算子权重：根据历史成功率动态调节各邻域算子的被选中概率（加速收敛）
    - 精英池后优化：主循环结束后对精英池中的多组候选解执行 VND，提升最终解稳定性
    """

    def __init__(self, city_indices: list[int], spots_dict: dict[int, SpotDict],
                 travel_speed: float = 1.0, penalty_weight: float = 100.0,
                 early_wait_weight: float = 0.1, late_return_weight: float = 50.0,
                 depot_index: int = 0, use_real_time_matrix: bool = False,
                 **kwargs) -> None:
        """
        初始化 VNS 求解器。

        Args:
            city_indices: 需要规划路径的城市索引列表。
            spots_dict: 景点字典，每项含 {"tw": (start, end), "stay": float}。
            travel_speed: 旅行速度（距离/时间单位）。use_real_time_matrix=True 时无效。
            penalty_weight: 迟到惩罚权重。
            early_wait_weight: 早到等待惩罚权重。
            late_return_weight: 晚归惩罚权重。
            depot_index: 起终点索引（默认为 0）。
            use_real_time_matrix: 是否使用高德真实旅行时间矩阵。
            **kwargs: 覆盖 VNS_DEFAULT_PARAMS 的额外参数。
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

        self.params = VNS_DEFAULT_PARAMS.copy()
        self.params.update(kwargs)

        # Numba 预提取数组
        n = len(spots_dict)
        self.spots_start = np.array([spots_dict[i]["tw"][0] for i in range(n)], dtype=np.float64)
        self.spots_end   = np.array([spots_dict[i]["tw"][1] for i in range(n)], dtype=np.float64)
        self.spots_stay  = np.array([spots_dict[i]["stay"] for i in range(n)], dtype=np.float64)

        # 适应度缓存：避免同一解重复触发 Numba 调用的开销
        # 警告：key 使用 id(cost_mat) 而非矩阵哈希（避免哈希开销），
        # 若矩阵对象内容被修改则缓存不会失效，可能返回错误结果
        # 另：当前无容量限制，长迭代场景下存在内存膨胀风险；小规模景点数（<200）下可忽略
        self.fitness_cache = {}
        # 精英池：保留搜索过程中最优的几条路径
        self.elite_pool = []
        # 自适应算子权重：让历史上更有效的算子获得更高被选中概率，加速收敛
        self.operator_weights = {'swap': 1.0, 'inversion': 1.0, 'insert': 1.0, '2opt': 1.0}
        self.last_operator = None

    # ---------- 适应度（带缓存） ----------

    def _cal_fitness(self, line: list[int], cost_mat: np.ndarray) -> Tuple[float, float, float]:
        """带缓存的适应度计算，避免重复触发 Numba 调用的开销

        Args:
            line: 路径列表（含起终点的完整路径）。
            cost_mat: 距离/旅行时间矩阵。

        Returns:
            Tuple[float, float, float]: (总成本, 旅行累积值, 时间惩罚).
        """
        key = (tuple(line), id(cost_mat))
        if key in self.fitness_cache:
            return self.fitness_cache[key]
        line_arr = np.array(line, dtype=np.int32)
        dis_arr = np.asarray(cost_mat, dtype=np.float64)
        result = _cal_fitness_numba(
            line_arr, dis_arr,
            self.travel_speed, self.penalty_weight,
            self.early_wait_weight, self.late_return_weight,
            self.depot_index,
            self.spots_start, self.spots_end, self.spots_stay,
            self.use_real_time_matrix
        )
        self.fitness_cache[key] = result
        return result

    # ---------- 初始解生成 ----------

    def _init_nearest_neighbor(self, cost_mat: np.ndarray) -> list[int]:
        """最近邻贪心初始解：从未访问节点中选成本最小的加入路径。"""
        unvisited = set(self.city_indices)
        route = [self.depot_index]
        cur = self.depot_index
        while unvisited:
            best = min(unvisited, key=lambda n: cost_mat[cur][n] if cost_mat is not None else 999999)
            route.append(best)
            unvisited.remove(best)
            cur = best
        route.append(self.depot_index)
        return route

    def _init_time_window(self) -> list[int]:
        """按时间窗起始排序生成初始解（启发式，起终点闭合路径）。"""
        if self.num_cities > 0:
            cities_with_time = [(c, self.spots_dict[c]["tw"][0]) for c in self.city_indices]
            cities_with_time.sort(key=lambda x: x[1])
            return [self.depot_index] + [c for c, _ in cities_with_time] + [self.depot_index]
        return [self.depot_index, self.depot_index]

    def _init_random(self) -> list[int]:
        """随机排列初始解：提供种群多样性，防止陷入局部最优。"""
        route = self.city_indices.copy()
        random.shuffle(route)
        return [self.depot_index] + route + [self.depot_index]

    # ---------- 邻域算子 ----------

    def _swap(self, route: list[int]) -> list[int]:
        """Swap 算子：随机交换两个内部节点，改变路径结构。

        Args:
            route: 当前路径。

        Returns:
            List[int]: 扰动后的路径。
        """
        r = route.copy()
        inner = r[1:-1]
        if len(inner) < 2: return r
        i, j = random.sample(range(len(inner)), 2)
        inner[i], inner[j] = inner[j], inner[i]
        r[1:-1] = inner
        return r

    def _inversion(self, route: list[int]) -> list[int]:
        """Inversion 算子：反转内部一段子序列，改变路径拓扑。

        Args:
            route: 当前路径。

        Returns:
            List[int]: 扰动后的路径。
        """
        r = route.copy()
        inner = r[1:-1]
        if len(inner) < 2: return r
        i = random.randint(0, len(inner) - 2)
        j = random.randint(i + 1, len(inner) - 1)
        inner[i:j + 1] = reversed(inner[i:j + 1])
        r[1:-1] = inner
        return r

    def _insert(self, route: list[int]) -> list[int]:
        """Insert 算子：随机删除一个节点并插入到另一位置，改变路径结构。

        Args:
            route: 当前路径。

        Returns:
            List[int]: 扰动后的路径。
        """
        r = route.copy()
        inner = r[1:-1]
        if len(inner) < 2: return r
        i = random.randint(0, len(inner) - 1)
        j = random.randint(0, len(inner) - 1)
        while i == j:
            j = random.randint(0, len(inner) - 1)
        val = inner.pop(i)
        inner.insert(j, val)
        r[1:-1] = inner
        return r

    def _2opt(self, route: list[int]) -> list[int]:
        """2-opt 算子：反转内部两个切割点之间的子序列，消除路径交叉。

        Args:
            route: 当前路径。

        Returns:
            List[int]: 扰动后的路径。
        """
        r = route.copy()
        inner = r[1:-1]
        if len(inner) < 3: return r
        i = random.randint(0, len(inner) - 3)
        j = random.randint(i + 2, len(inner) - 1)
        inner[i:j+1] = reversed(inner[i:j+1])
        r[1:-1] = inner
        return r

    # ---------- Shaking（抖动） ----------

    def _shaking(self, solution, k, cost_mat, iter_ratio=0.5):
        """
        执行 k 步抖动。

        搜索早期优先对违反时间窗的节点做针对性扰动，
        后期退化到随机算子 + 自适应权重。

        Args:
            solution: 当前解路径。
            k: 抖动步数。
            cost_mat: 距离矩阵。
            iter_ratio: 当前迭代进度比例（0~1）。

        Returns:
            Tuple[List[int], str | None]: (抖动后的解, 最后使用的算子名称).
        """
        sol = solution.copy()
        ops = ['swap', 'inversion', 'insert', '2opt']

        # 收集违规节点
        # 注意：analyze_solution（Python 版）与 _cal_fitness_numba（Numba 版）逻辑需同步
        violators = []
        if iter_ratio < EARLY_EXPLORE_RATIO and cost_mat is not None:
            _, _, _, _, violations = analyze_solution(
                sol, cost_mat, self.spots_dict, self.travel_speed,
                self.early_wait_weight, self.penalty_weight,
                self.late_return_weight, self.depot_index,
                use_real_time_matrix=self.use_real_time_matrix
            )
            violators = list(set(v[0] for v in violations))

        last_op = None
        for step in range(k):
            if iter_ratio < EARLY_EXPLORE_RATIO and violators:
                # 早期阶段对违规节点实施定向扰动，加速可行解的发现
                if random.random() < VIOLATOR_TARGET_PROB:
                    target = random.choice(violators)
                    op = random.choice(ops)
                    sol = self._perturb_around(sol, target, op)
                    last_op = op
                    continue

            # 自适应权重选择算子
            weights = [self.operator_weights[op] for op in ops]
            op = random.choices(ops, weights=weights)[0]
            last_op = op

            if op == 'swap': sol = self._swap(sol)
            elif op == 'inversion': sol = self._inversion(sol)
            elif op == 'insert': sol = self._insert(sol)
            elif op == '2opt': sol = self._2opt(sol)

        return sol, last_op

    def _perturb_around(self, route, target, op):
        """针对特定节点进行扰动（对其附近片段操作）

        Args:
            route: 当前路径。
            target: 目标节点索引。
            op (str): 使用的扰动算子，可选 'swap'/'inversion'/'insert'。

        Returns:
            List[int]: 扰动后的路径。
        """
        inner = route[1:-1]
        if target not in inner:
            return route
        idx = inner.index(target)
        if op == 'swap' and len(inner) >= 2:
            j = (idx + 1) % len(inner)
            inner[idx], inner[j] = inner[j], inner[idx]
        elif op == 'inversion' and idx + 2 < len(inner):
            inner[idx:idx+3] = reversed(inner[idx:idx+3])
        elif op == 'insert' and len(inner) >= 2:
            j = (idx + 2) % len(inner)
            val = inner.pop(idx)
            inner.insert(j, val)
        route[1:-1] = inner
        return route

    # ---------- VND 局部搜索 ----------

    def _local_search(self, solution, cost_mat, move_type):
        """
        指定邻域类型的第一改善型局部搜索。

        遍历所有合法操作对，找到第一个改善即返回（First Improvement）。

        Args:
            solution: 当前解路径。
            cost_mat: 距离矩阵。
            move_type (str): 邻域类型，可选 'swap'/'inversion'/'insert'/'2opt'。

        Returns:
            List[int]: 局部搜索后的路径。
        """
        best_sol = solution.copy()
        best_cost, _, _ = self._cal_fitness(best_sol, cost_mat)
        inner = best_sol[1:-1]
        n = len(inner)

        if move_type == 'swap':
            for i in range(n - 1):
                for j in range(i + 1, n):
                    new_inner = inner.copy()
                    new_inner[i], new_inner[j] = new_inner[j], new_inner[i]
                    new_sol = [self.depot_index] + new_inner + [self.depot_index]
                    c, _, _ = self._cal_fitness(new_sol, cost_mat)
                    if c < best_cost:
                        return new_sol
        elif move_type == 'inversion':
            for i in range(n - 1):
                for j in range(i + 2, n):
                    new_inner = inner[:i] + inner[i:j+1][::-1] + inner[j+1:]
                    new_sol = [self.depot_index] + new_inner + [self.depot_index]
                    c, _, _ = self._cal_fitness(new_sol, cost_mat)
                    if c < best_cost:
                        return new_sol
        elif move_type == 'insert':
            for i in range(n):
                for j in range(n):
                    if i == j: continue
                    new_inner = inner.copy()
                    val = new_inner.pop(i)
                    new_inner.insert(j, val)
                    new_sol = [self.depot_index] + new_inner + [self.depot_index]
                    c, _, _ = self._cal_fitness(new_sol, cost_mat)
                    if c < best_cost:
                        return new_sol
        elif move_type == '2opt':
            for i in range(n - 1):
                for j in range(i + 2, n):
                    new_inner = inner[:i] + inner[i:j+1][::-1] + inner[j+1:]
                    new_sol = [self.depot_index] + new_inner + [self.depot_index]
                    c, _, _ = self._cal_fitness(new_sol, cost_mat)
                    if c < best_cost:
                        return new_sol
        return best_sol

    def _vnd(self, solution, cost_mat):
        """
        变邻域下降（Variable Neighborhood Descent）。

        依次尝试 swap → inversion → insert → 2opt，
        任一邻域改善则回到第一个邻域重新搜索。

        Args:
            solution: 当前解路径。
            cost_mat: 距离矩阵。

        Returns:
            List[int]: VND 优化后的路径。
        """
        sol = solution.copy()
        k = 0
        neighborhoods = ['swap', 'inversion', 'insert', '2opt']

        while k < len(neighborhoods):
            sol_new = self._local_search(sol, cost_mat, neighborhoods[k])
            new_cost, _, _ = self._cal_fitness(sol_new, cost_mat)
            old_cost, _, _ = self._cal_fitness(sol, cost_mat)
            if new_cost < old_cost:
                sol = sol_new
                k = 0
            else:
                k += 1
        return sol

    # ---------- 精英池管理 ----------

    def _update_elite(self, solution, cost):
        """将解加入精英池，超出容量时替换最差者。

        Args:
            solution: 当前解路径。
            cost: 当前解成本。
        """
        if len(self.elite_pool) < self.params['elite_size']:
            self.elite_pool.append((solution.copy(), cost))
        else:
            worst_idx = max(range(len(self.elite_pool)), key=lambda i: self.elite_pool[i][1])
            if cost < self.elite_pool[worst_idx][1]:
                self.elite_pool[worst_idx] = (solution.copy(), cost)

    def get_elite_pool(self):
        """返回精英池（(解, 成本) 列表）"""
        return self.elite_pool

    # ---------- 主求解入口 ----------

    def solve(self, cost_mat, initial_solution=None):
        """
        执行 VNS 主循环。

        Args:
            cost_mat: 距离矩阵。
            initial_solution: 可选的初始解，None 则自动择优选取。

        Returns:
            dict: 包含以下键：
                - best_solution (List[int]): 最优路径（含起终点）。
                - best_cost (float): 最优总成本（旅行累积值 + 时间惩罚，单位由输入矩阵决定）。
                - best_distance (float): 旅行累积值。标准模式 = 总距离；真实模式 = 总旅行时间。
                - best_penalty (float): 最优路径总时间惩罚。
                - convergence_history (List[float]): 收敛曲线，每轮迭代后的最优成本。
        """
        # 选取初始解（就近 / 按时间窗 / 随机三选一）
        if initial_solution is not None:
            cur_sol = initial_solution
        else:
            candidates = [
                self._init_nearest_neighbor(cost_mat),
                self._init_time_window(),
                self._init_random()
            ]
            cur_sol = min(candidates, key=lambda s: self._cal_fitness(s, cost_mat)[0])

        cur_cost, cur_dist, cur_pen = self._cal_fitness(cur_sol, cost_mat)
        best_sol = cur_sol.copy()
        best_cost, best_dist, best_pen = cur_cost, cur_dist, cur_pen
        conv = [best_cost]

        self.elite_pool = [(best_sol.copy(), best_cost)]

        shaking_list = self.params['shaking_neighbors'].copy()
        no_improve = 0
        max_iter = self.params['max_iter']
        temperature = self.params['sa_initial_temp']

        for it in range(max_iter):
            iter_ratio = it / max_iter

            # 动态抖动强度：长期无改善时增加强度
            dynamic_max = min(5, max(shaking_list) + (1 if no_improve > DYNAMIC_STRENGTHEN_AFTER else 0))
            k = random.randint(1, dynamic_max)

            # Shake → VND
            x_shake, self.last_operator = self._shaking(cur_sol, k, cost_mat, iter_ratio)
            x_local = self._vnd(x_shake, cost_mat)

            new_cost, new_dist, new_pen = self._cal_fitness(x_local, cost_mat)
            delta = new_cost - cur_cost

            # SA 接收准则
            accept = delta < 0
            if not accept and temperature > 0:
                if random.random() < math.exp(-delta / temperature):
                    accept = True

            if accept:
                cur_sol, cur_cost, cur_dist, cur_pen = x_local, new_cost, new_dist, new_pen
                if new_cost < best_cost:
                    best_sol, best_cost, best_dist, best_pen = cur_sol.copy(), new_cost, new_dist, new_pen
                    no_improve = 0
                    self._update_elite(best_sol, best_cost)
                    # 自适应算子权重奖励：成功改善的算子获得 +2% 权重，让高效算子更易被选中
                    if self.last_operator:
                        self.operator_weights[self.last_operator] *= WEIGHT_REWARD_FACTOR
                        total = sum(self.operator_weights.values())
                        for op in self.operator_weights:
                            self.operator_weights[op] /= total
                # 改善但未超越全局最优，连续无改善计数递增
                else:
                    no_improve += 1
            # 未被接受，连续无改善计数递增，用于触发早停
            else:
                no_improve += 1

            conv.append(best_cost)
            temperature *= self.params['sa_cooling_rate']

            if no_improve >= self.params['no_improve_limit']:
                break

        # ***** 最终精细化：对最优解和精英池中的解额外执行 VND，提升最终解的质量稳定性 *****
        for _ in range(self.params['final_vnd_rounds']):
            refined = self._vnd(best_sol, cost_mat)
            r_cost, _, _ = self._cal_fitness(refined, cost_mat)
            if r_cost < best_cost:
                best_sol, best_cost = refined, r_cost

        for elite_sol, _ in self.elite_pool:
            refined = self._vnd(elite_sol, cost_mat)
            r_cost, r_dist, r_pen = self._cal_fitness(refined, cost_mat)
            if r_cost < best_cost:
                best_sol, best_cost, best_dist, best_pen = refined, r_cost, r_dist, r_pen

        return {
            'best_solution': best_sol,
            'best_cost': best_cost,
            'best_distance': best_dist,
            'best_penalty': best_pen,
            'convergence_history': conv
        }
