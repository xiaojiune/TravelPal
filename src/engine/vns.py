# src/engine/vns.py

import random
import math
import numpy as np
from numba import njit
from src.engine.fitness import analyze_solution

# ================== VNS 默认参数 ==================
# max_iter: VNS 主循环最大迭代次数
# shaking_neighbors: 抖动强度候选集合
# local_search_iter: 局部搜索迭代上限（当前未使用，保留扩展）
# no_improve_limit: 连续无改善时提前终止
# sa_initial_temp / sa_cooling_rate: SA 接收准则的初温与冷却率
# elite_size: 精英池容量
# final_vnd_rounds: 主循环结束后对精英解额外运行 VND 的轮数
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

# ================== Numba 适应度内核 ==================

@njit(cache=True)
def _cal_fitness_numba(line, dis_matrix, travel_speed, penalty_weight,
                       early_wait_weight, late_return_weight, depot_index,
                       spots_start, spots_end, spots_stay):
    """Numba JIT 编译的适应度计算内核（无 GIL、无 Python 对象调用）"""
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

    if current_time > depot_end:
        time_penalty += (current_time - depot_end) * late_return_weight

    total = dis_sum + time_penalty
    return round(total, 1), round(dis_sum, 1), round(time_penalty, 1)


# ================== VNSSolver 主类 ==================

class VNSSolver:
    """
    变邻域搜索求解器（Variable Neighborhood Search）。

    集成多种邻域结构（swap/inversion/insert/2opt）与 VND 局部搜索，
    通过 SA 准则控制扰动接受，并维护精英池保留历史最优解。
    """

    def __init__(self, city_indices, spots_dict, travel_speed=1.0,
                 penalty_weight=100.0, early_wait_weight=0.1,
                 late_return_weight=50.0, depot_index=0, **kwargs):
        """
        初始化 VNS 求解器。

        Args:
            city_indices: 需要规划路径的城市索引列表。
            spots_dict: 景点字典，每项含 {"tw": (start, end), "stay": float}。
            travel_speed: 旅行速度（距离/时间单位）。
            penalty_weight: 迟到惩罚权重。
            early_wait_weight: 早到等待惩罚权重。
            late_return_weight: 晚归惩罚权重。
            depot_index: 起终点索引（默认为 0）。
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

        self.params = VNS_DEFAULT_PARAMS.copy()
        self.params.update(kwargs)

        # Numba 预提取数组
        n = len(spots_dict)
        self.spots_start = np.array([spots_dict[i]["tw"][0] for i in range(n)], dtype=np.float64)
        self.spots_end   = np.array([spots_dict[i]["tw"][1] for i in range(n)], dtype=np.float64)
        self.spots_stay  = np.array([spots_dict[i]["stay"] for i in range(n)], dtype=np.float64)

        # 适应度缓存（解 → 成本的记忆化映射）
        self.fitness_cache = {}
        # 精英池：保留搜索过程中最优的几条路径
        self.elite_pool = []
        # 自适应算子权重：成功改善解的算子获得增量奖励
        self.operator_weights = {'swap': 1.0, 'inversion': 1.0, 'insert': 1.0, '2opt': 1.0}
        self.last_operator = None

    # ---------- 适应度（带缓存） ----------

    def _cal_fitness(self, line, dis_matrix):
        """带缓存的适应度计算，避免重复评估同一路径"""
        key = (tuple(line), id(dis_matrix))
        if key in self.fitness_cache:
            return self.fitness_cache[key]
        line_arr = np.array(line, dtype=np.int32)
        dis_arr = np.asarray(dis_matrix, dtype=np.float64)
        result = _cal_fitness_numba(
            line_arr, dis_arr,
            self.travel_speed, self.penalty_weight,
            self.early_wait_weight, self.late_return_weight,
            self.depot_index,
            self.spots_start, self.spots_end, self.spots_stay
        )
        self.fitness_cache[key] = result
        return result

    # ---------- 初始解生成 ----------

    def _init_nearest_neighbor(self, dis_matrix):
        """最近邻贪心初始解"""
        unvisited = set(self.city_indices)
        route = [self.depot_index]
        cur = self.depot_index
        while unvisited:
            best = min(unvisited, key=lambda n: dis_matrix[cur][n] if dis_matrix is not None else 999999)
            route.append(best)
            unvisited.remove(best)
            cur = best
        route.append(self.depot_index)
        return route

    def _init_time_window(self):
        """按时间窗起始时间排序的初始解"""
        if self.num_cities > 0:
            cities_with_time = [(c, self.spots_dict[c]["tw"][0]) for c in self.city_indices]
            cities_with_time.sort(key=lambda x: x[1])
            return [self.depot_index] + [c for c, _ in cities_with_time] + [self.depot_index]
        return [self.depot_index, self.depot_index]

    def _init_random(self):
        """随机排列初始解"""
        route = self.city_indices.copy()
        random.shuffle(route)
        return [self.depot_index] + route + [self.depot_index]

    # ---------- 邻域算子 ----------

    def _swap(self, route):
        """Swap 算子：交换内部两点位置"""
        r = route.copy()
        inner = r[1:-1]
        if len(inner) < 2: return r
        i, j = random.sample(range(len(inner)), 2)
        inner[i], inner[j] = inner[j], inner[i]
        r[1:-1] = inner
        return r

    def _inversion(self, route):
        """Inversion 算子：反转内部一段子序列"""
        r = route.copy()
        inner = r[1:-1]
        if len(inner) < 2: return r
        i = random.randint(0, len(inner) - 2)
        j = random.randint(i + 1, len(inner) - 1)
        inner[i:j + 1] = reversed(inner[i:j + 1])
        r[1:-1] = inner
        return r

    def _insert(self, route):
        """Insert 算子：随机删除一个节点并插入到另一位置"""
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

    def _2opt(self, route):
        """2-opt 算子：反转内部两个切割点之间的子序列"""
        r = route.copy()
        inner = r[1:-1]
        if len(inner) < 3: return r
        i = random.randint(0, len(inner) - 3)
        j = random.randint(i + 2, len(inner) - 1)
        inner[i:j+1] = reversed(inner[i:j+1])
        r[1:-1] = inner
        return r

    # ---------- Shaking（抖动） ----------

    def _shaking(self, solution, k, dis_matrix, iter_ratio=0.5):
        """
        执行 k 步抖动。

        搜索早期（iter_ratio < 0.3）优先对违反时间窗的节点做针对性扰动，
        后期退化到随机算子 + 自适应权重。
        """
        sol = solution.copy()
        ops = ['swap', 'inversion', 'insert', '2opt']

        # 收集违规节点
        violators = []
        if iter_ratio < 0.3 and dis_matrix is not None:
            _, _, _, _, violations = analyze_solution(
                sol, dis_matrix, self.spots_dict, self.travel_speed,
                self.early_wait_weight, self.penalty_weight,
                self.late_return_weight, self.depot_index
            )
            violators = list(set(v[0] for v in violations))

        last_op = None
        for step in range(k):
            if iter_ratio < 0.3 and violators:
                # 早期阶段，60% 概率对违规节点实施定向扰动
                if random.random() < 0.6:
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
        """针对特定节点进行扰动（对其附近片段操作）"""
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

    def _local_search(self, solution, dis_matrix, move_type):
        """
        指定邻域类型的第一改善型局部搜索。

        遍历所有合法操作对，找到第一个改善即返回（First Improvement）。
        """
        best_sol = solution.copy()
        best_cost, _, _ = self._cal_fitness(best_sol, dis_matrix)
        inner = best_sol[1:-1]
        n = len(inner)

        if move_type == 'swap':
            for i in range(n - 1):
                for j in range(i + 1, n):
                    new_inner = inner.copy()
                    new_inner[i], new_inner[j] = new_inner[j], new_inner[i]
                    new_sol = [self.depot_index] + new_inner + [self.depot_index]
                    c, _, _ = self._cal_fitness(new_sol, dis_matrix)
                    if c < best_cost:
                        return new_sol
        elif move_type == 'inversion':
            for i in range(n - 1):
                for j in range(i + 2, n):
                    new_inner = inner[:i] + inner[i:j+1][::-1] + inner[j+1:]
                    new_sol = [self.depot_index] + new_inner + [self.depot_index]
                    c, _, _ = self._cal_fitness(new_sol, dis_matrix)
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
                    c, _, _ = self._cal_fitness(new_sol, dis_matrix)
                    if c < best_cost:
                        return new_sol
        elif move_type == '2opt':
            for i in range(n - 1):
                for j in range(i + 2, n):
                    new_inner = inner[:i] + inner[i:j+1][::-1] + inner[j+1:]
                    new_sol = [self.depot_index] + new_inner + [self.depot_index]
                    c, _, _ = self._cal_fitness(new_sol, dis_matrix)
                    if c < best_cost:
                        return new_sol
        return best_sol

    def _vnd(self, solution, dis_matrix):
        """
        变邻域下降（Variable Neighborhood Descent）。

        依次尝试 swap → inversion → insert → 2opt，
        任一邻域改善则回到第一个邻域重新搜索。
        """
        sol = solution.copy()
        k = 0
        neighborhoods = ['swap', 'inversion', 'insert', '2opt']

        while k < len(neighborhoods):
            sol_new = self._local_search(sol, dis_matrix, neighborhoods[k])
            new_cost, _, _ = self._cal_fitness(sol_new, dis_matrix)
            old_cost, _, _ = self._cal_fitness(sol, dis_matrix)
            if new_cost < old_cost:
                sol = sol_new
                k = 0
            else:
                k += 1
        return sol

    # ---------- 精英池管理 ----------

    def _update_elite(self, solution, cost):
        """将解加入精英池，超出容量时替换最差者"""
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

    def solve(self, dis_matrix, initial_solution=None):
        """
        执行 VNS 主循环。

        Args:
            dis_matrix: 距离矩阵。
            initial_solution: 可选的初始解，None 则自动择优选取。

        Returns:
            dict: {'best_solution', 'best_cost', 'best_distance', 'best_penalty', 'convergence_history'}
        """
        # 选取初始解（就近 / 按时间窗 / 随机三选一）
        if initial_solution is not None:
            cur_sol = initial_solution
        else:
            candidates = [
                self._init_nearest_neighbor(dis_matrix),
                self._init_time_window(),
                self._init_random()
            ]
            cur_sol = min(candidates, key=lambda s: self._cal_fitness(s, dis_matrix)[0])

        cur_cost, cur_dist, cur_pen = self._cal_fitness(cur_sol, dis_matrix)
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
            dynamic_max = min(5, max(shaking_list) + (1 if no_improve > 10 else 0))
            k = random.randint(1, dynamic_max)

            # Shake → VND
            x_shake, self.last_operator = self._shaking(cur_sol, k, dis_matrix, iter_ratio)
            x_local = self._vnd(x_shake, dis_matrix)

            new_cost, new_dist, new_pen = self._cal_fitness(x_local, dis_matrix)
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
                    # 自适应算子权重：成功改善的算子获得 +2% 权重奖励
                    if self.last_operator:
                        self.operator_weights[self.last_operator] *= 1.02
                        total = sum(self.operator_weights.values())
                        for op in self.operator_weights:
                            self.operator_weights[op] /= total
                else:
                    no_improve += 1
            else:
                no_improve += 1

            conv.append(best_cost)
            temperature *= self.params['sa_cooling_rate']

            if no_improve >= self.params['no_improve_limit']:
                break

        # ***** 最终精细化：对最优解和精英池中的解执行多轮 VND *****
        for _ in range(self.params['final_vnd_rounds']):
            refined = self._vnd(best_sol, dis_matrix)
            r_cost, _, _ = self._cal_fitness(refined, dis_matrix)
            if r_cost < best_cost:
                best_sol, best_cost = refined, r_cost

        for elite_sol, _ in self.elite_pool:
            refined = self._vnd(elite_sol, dis_matrix)
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
