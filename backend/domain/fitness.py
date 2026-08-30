"""路径成本与违规详情分析。"""

from typing import Tuple

import numpy as np
from numba import njit

# ================== Numba 适应度内核（CA / VNS 共享） ==================


@njit(cache=True)
def _cal_fitness_numba(
    line: np.ndarray,
    cost_mat: np.ndarray,
    penalty_weight: float,
    early_wait_weight: float,
    late_return_weight: float,
    depot_index: int,
    spots_start: np.ndarray,
    spots_end: np.ndarray,
    spots_stay: np.ndarray,
) -> Tuple[float, float, float]:
    """
    Numba JIT 编译的适应度计算内核。

    沿路径逐段模拟行程，累计总成本与时间惩罚。
    路径必须从 depot 出发并回到 depot，长度不足 3 时返回极大惩罚值。
    成本矩阵元素为旅行时间（分钟），d 直接作为 travel_time 使用。

    Args:
        line: 路径数组（含起终点的完整路径）。
        cost_mat: 旅行时间矩阵（分钟）。
        penalty_weight: 迟到惩罚权重。
        early_wait_weight: 早到等待惩罚权重。
        late_return_weight: 晚归惩罚权重。
        depot_index: 起终点索引。
        spots_start: 各景点时间窗开始时间数组。
        spots_end: 各景点时间窗结束时间数组。
        spots_stay: 各景点停留时长数组。

    Returns:
        Tuple[float, float, float]: (总成本, 旅行累积值, 时间惩罚).
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
        travel_time = d
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
    return round(total, 1), round(travel_sum, 1), round(time_penalty, 1)  # pyright: ignore[reportCallIssue, reportArgumentType]


def analyze_solution(
    line: list,
    cost_mat: np.ndarray,
    spots_dict: dict,
    early_wait_weight=0.1,
    penalty_weight=100.0,
    late_return_weight=50.0,
    depot=0,
):
    """
    解析指定路径的详细成本与违规信息。

    逐段模拟路径执行过程，累计旅行成本、早到等待惩罚、迟到惩罚和晚归惩罚。
    成本矩阵元素为旅行时间（分钟），d 直接作为 travel_time 使用。

    Args:
        line: 路径列表（含起终点）。
        cost_mat: 旅行时间矩阵（分钟）。
        spots_dict: 景点字典，每项含 {"tw": (start, end), "stay": float}。
        early_wait_weight: 早到等待惩罚权重。
        penalty_weight: 迟到惩罚权重。
        late_return_weight: 晚归惩罚权重。
        depot: 起终点索引。

    Returns:
        Tuple[float, float, float, float, List]: (总成本, 旅行累积值, 等待惩罚, 迟到惩罚, 违规详情列表).
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
        travel_time = d
        arrival = current_time + travel_time

        if to != depot:
            start_t, end_t, stay = spots_dict[to]["tw"][0], spots_dict[to]["tw"][1], spots_dict[to]["stay"]
            if arrival < start_t:
                wait = start_t - arrival
                wait_penalty += wait * early_wait_weight
                current_time = start_t + stay
                violations.append((to, "wait", wait))
            elif arrival > end_t:
                late = arrival - end_t
                late_penalty += late * penalty_weight
                current_time = arrival + stay
                violations.append((to, "late", late))
            else:
                current_time = arrival + stay
        else:
            if arrival > depot_end:
                late_penalty += (arrival - depot_end) * late_return_weight
            current_time = arrival

    total_penalty = wait_penalty + late_penalty
    total_cost = travel_sum + total_penalty
    return round(total_cost, 1), round(travel_sum, 1), round(wait_penalty, 1), round(late_penalty, 1), violations  # pyright: ignore[reportCallIssue, reportArgumentType]
