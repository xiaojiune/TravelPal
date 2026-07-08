# ================== 路径成本分析 ==================


import numpy as np


def analyze_solution(line: list, cost_mat: np.ndarray, spots_dict: dict, travel_speed: float,
                     early_wait_weight=0.1,
                     penalty_weight=100.0,
                     late_return_weight=50.0,
                     depot=0,
                     use_real_time_matrix=False):
    """
    解析指定路径的详细成本与违规信息。

    逐段模拟路径执行过程，累计旅行成本、早到等待惩罚、迟到惩罚和晚归惩罚。

    Args:
        line: 路径列表（含起终点）。
        cost_mat: 距离/旅行时间矩阵。
        spots_dict: 景点字典，每项含 {"tw": (start, end), "stay": float}。
        travel_speed: 旅行速度（距离/时间单位）。use_real_time_matrix=True 时无效。
        early_wait_weight: 早到等待惩罚权重。
        penalty_weight: 迟到惩罚权重。
        late_return_weight: 晚归惩罚权重。
        depot: 起终点索引。
        use_real_time_matrix: 矩阵是否为旅行时间（避免 d / travel_speed 重复计算）。

    Returns:
        Tuple[float, float, float, float, List]: (总成本, 旅行累积值, 等待惩罚, 迟到惩罚, 违规详情列表).
            旅行累积值：标准模式 = 总距离，真实模式 = 总旅行时间。
            违规详情项为 (节点索引, 违规类型, 时长)，违规类型为 'wait' 或 'late'。
    """
    travel_sum = 0
    wait_penalty = 0
    late_penalty = 0
    depot_start = spots_dict[depot]["tw"][0]
    depot_end = spots_dict[depot]["tw"][1]
    current_time = depot_start
    violations = []

    for i in range(len(line) - 1):
        fr, to = line[i], line[i + 1]
        d = cost_mat[fr][to]
        travel_sum += d
        travel_time = d if use_real_time_matrix else d / travel_speed
        arrival = current_time + travel_time

        if to != depot:
            start_t, end_t, stay = spots_dict[to]["tw"][0], spots_dict[to]["tw"][1], spots_dict[to]["stay"]
            if arrival < start_t:
                wait = start_t - arrival
                wait_penalty += wait * early_wait_weight
                current_time = start_t + stay
                violations.append((to, 'wait', wait))
            elif arrival > end_t:
                late = arrival - end_t
                late_penalty += late * penalty_weight
                current_time = arrival + stay
                violations.append((to, 'late', late))
            else:
                current_time = arrival + stay
        else:
            if arrival > depot_end:
                late_penalty += (arrival - depot_end) * late_return_weight
            current_time = arrival

    total_penalty = wait_penalty + late_penalty
    total_cost = travel_sum + total_penalty
    return round(total_cost, 1), round(travel_sum, 1), round(wait_penalty, 1), round(late_penalty, 1), violations
