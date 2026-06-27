import random
import math
import numpy as np
from numba import njit
from src.engine.fitness import analyze_solution

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

@njit(cache=True)
def _cal_fitness_numba(line, dis_matrix, travel_speed, penalty_weight,
                       early_wait_weight, late_return_weight, depot_index,
                       spots_start, spots_end, spots_stay):
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


class VNSSolver:
    def __init__(self, city_indices, spots_dict, travel_speed=1.0,
                 penalty_weight=100.0, early_wait_weight=0.1,
                 late_return_weight=50.0, depot_index=0, **kwargs):
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

        n = len(spots_dict)
        self.spots_start = np.array([spots_dict[i]["tw"][0] for i in range(n)], dtype=np.float64)
        self.spots_end   = np.array([spots_dict[i]["tw"][1] for i in range(n)], dtype=np.float64)
        self.spots_stay  = np.array([spots_dict[i]["stay"] for i in range(n)], dtype=np.float64)

        self.fitness_cache = {}
        self.elite_pool = []
        self.operator_weights = {'swap': 1.0, 'inversion': 1.0, 'insert': 1.0, '2opt': 1.0}
        self.last_operator = None

    def _cal_fitness(self, line, dis_matrix):
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

    def _init_nearest_neighbor(self, dis_matrix):
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
        if self.num_cities > 0:
            cities_with_time = [(c, self.spots_dict[c]["tw"][0]) for c in self.city_indices]
            cities_with_time.sort(key=lambda x: x[1])
            return [self.depot_index] + [c for c, _ in cities_with_time] + [self.depot_index]
        return [self.depot_index, self.depot_index]

    def _init_random(self):
        route = self.city_indices.copy()
        random.shuffle(route)
        return [self.depot_index] + route + [self.depot_index]

    def _swap(self, route):
        r = route.copy()
        inner = r[1:-1]
        if len(inner) < 2: return r
        i, j = random.sample(range(len(inner)), 2)
        inner[i], inner[j] = inner[j], inner[i]
        r[1:-1] = inner
        return r

    def _inversion(self, route):
        r = route.copy()
        inner = r[1:-1]
        if len(inner) < 2: return r
        i = random.randint(0, len(inner) - 2)
        j = random.randint(i + 1, len(inner) - 1)
        inner[i:j + 1] = reversed(inner[i:j + 1])
        r[1:-1] = inner
        return r

    def _insert(self, route):
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
        r = route.copy()
        inner = r[1:-1]
        if len(inner) < 3: return r
        i = random.randint(0, len(inner) - 3)
        j = random.randint(i + 2, len(inner) - 1)
        inner[i:j+1] = reversed(inner[i:j+1])
        r[1:-1] = inner
        return r

    def _shaking(self, solution, k, dis_matrix, iter_ratio=0.5):
        sol = solution.copy()
        ops = ['swap', 'inversion', 'insert', '2opt']

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
                if random.random() < 0.6:
                    target = random.choice(violators)
                    op = random.choice(ops)
                    sol = self._perturb_around(sol, target, op)
                    last_op = op
                    continue

            weights = [self.operator_weights[op] for op in ops]
            op = random.choices(ops, weights=weights)[0]
            last_op = op

            if op == 'swap': sol = self._swap(sol)
            elif op == 'inversion': sol = self._inversion(sol)
            elif op == 'insert': sol = self._insert(sol)
            elif op == '2opt': sol = self._2opt(sol)

        return sol, last_op

    def _perturb_around(self, route, target, op):
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

    def _local_search(self, solution, dis_matrix, move_type):
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

    def _update_elite(self, solution, cost):
        if len(self.elite_pool) < self.params['elite_size']:
            self.elite_pool.append((solution.copy(), cost))
        else:
            worst_idx = max(range(len(self.elite_pool)), key=lambda i: self.elite_pool[i][1])
            if cost < self.elite_pool[worst_idx][1]:
                self.elite_pool[worst_idx] = (solution.copy(), cost)

    def get_elite_pool(self):
        return self.elite_pool

    def solve(self, dis_matrix, initial_solution=None):
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

            dynamic_max = min(5, max(shaking_list) + (1 if no_improve > 10 else 0))
            k = random.randint(1, dynamic_max)

            x_shake, self.last_operator = self._shaking(cur_sol, k, dis_matrix, iter_ratio)

            x_local = self._vnd(x_shake, dis_matrix)

            new_cost, new_dist, new_pen = self._cal_fitness(x_local, dis_matrix)
            delta = new_cost - cur_cost

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
