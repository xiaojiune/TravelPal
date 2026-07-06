import time, os, warnings
import numpy as np

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
os.environ["OMP_NUM_THREADS"] = "1"

from backend.data.amap_loader import build_real_data
from backend.engine.search import cluster_and_solve, balance_groups, solve_groups

TRAVEL_SPEED = 1.0


def run_planning(poi_cache, city, hotel_name,
                 penalty_weight, early_wait_weight, late_return_weight,
                 mode="fast", n_days=None):
    """
    双阶段流程编排入口。

    加载真实数据 → 构建景点字典 → 执行 cluster_and_solve → 生成每日行程 → 返回前端可视乎化数据。

    Args:
        poi_cache: 包含 hotel 和 spots 的缓存数据（由前端/外部传入）。
        city: 城市名，用于高德 API 查询和文件命名。
        hotel_name: 酒店名称。
        penalty_weight: 违规惩罚权重。
        early_wait_weight: 早到等待惩罚权重。
        late_return_weight: 晚归惩罚权重。
        mode: "fast" 或 "deep"。
        n_days: 行程天数（可选）。

    Returns:
        dict: type="suggestion"（未指定天数）或包含 solution、best_days、daily_schedules 等。
    """
    total_start = time.time()

    poi_names = [hotel_name] + [s["name"] for s in poi_cache["spots"]]
    coords = [(poi_cache["hotel"]["lon"], poi_cache["hotel"]["lat"])] + \
             [(s["lon"], s["lat"]) for s in poi_cache["spots"]]

    print("正在调用驾车API计算成本矩阵...")
    cost_matrix_hours, dist_matrix, polylines = build_real_data(poi_names, coords)
    cost_matrix = np.round(cost_matrix_hours * 60, 0)
    print("成本矩阵构建完成。\n")

    spots = {0: {"name": hotel_name, "tw": poi_cache["hotel"]["tw"], "stay": 0,
                 "x": poi_cache["hotel"]["lon"], "y": poi_cache["hotel"]["lat"],
                 "original_tw": poi_cache["hotel"]["tw"]}}
    for i, spot in enumerate(poi_cache["spots"], start=1):
        tw_start = spot["tw"][0]
        tw_end = spot["tw"][1]
        # 将时间窗收缩为实际可用时段：到达之后才开放、关闭之前需留足停留时间
        expected_arrival = spot.get("expected_arrival", tw_start)
        effective_start = max(tw_start, expected_arrival)
        effective_end = tw_end - spot["stay"]
        spots[i] = {"name": spot["name"],
                    "tw": (effective_start, effective_end),
                    "original_tw": (tw_start, tw_end),
                    "stay": spot["stay"],
                    "x": spot["lon"], "y": spot["lat"]}

    depot = 0

    result = cluster_and_solve(
        spots, depot, cost_matrix, mode=mode,
        n_days=n_days,
        travel_speed=TRAVEL_SPEED,
        penalty_weight=penalty_weight,
        early_wait_weight=early_wait_weight,
        late_return_weight=late_return_weight,
    )

    if result["type"] == "suggestion":
        return result

    solution = result["solution"]
    print(f"最优总成本 ({mode} 模式): {solution['total_cost']:.1f}\n")

    dataset_name = f"{city}_{len(poi_names)-1}spots_{result['best_days']}日游"

    daily_schedules = []
    for day_idx, route in enumerate(solution["routes"]):
        schedule = []
        current_time = spots[0]["tw"][0]
        for i in range(len(route) - 1):
            from_node = route[i]
            to_node = route[i + 1]
            travel_time = dist_matrix[from_node][to_node]
            arrival_time = round(current_time + travel_time)

            if to_node != 0:
                original_start, original_end = spots[to_node]["original_tw"]
                effective_start, effective_end = spots[to_node]["tw"]
                stay = spots[to_node]["stay"]

                # 到达维度：早到需等待，晚到则违规；离开维度：若实际离开时间超过原始关门时间算晚归
                wait_time = max(0, effective_start - arrival_time)
                late_arrival = max(0, arrival_time - effective_end)
                actual_start = max(arrival_time, effective_start)
                departure_time = actual_start + stay
                late_departure = max(0, departure_time - original_end)

                late_arrival_int = int(late_arrival)
                wait_time_int = int(wait_time)
                late_departure_int = int(late_departure)

                if late_arrival_int > 0:
                    arrival_status = f"迟到 {late_arrival_int} 分钟"
                elif wait_time_int > 0:
                    arrival_status = f"早到 {wait_time_int} 分钟"
                else:
                    arrival_status = "正常到达"

                if late_departure_int > 0:
                    departure_status = f"迟到 {late_departure_int} 分钟离开"
                else:
                    departure_status = "正常离开"

                tw_str = f"{int(original_start // 60):02d}:{int(original_start % 60):02d} - {int(original_end // 60):02d}:{int(original_end % 60):02d}"
                stay_str = f"{stay} min" if stay > 0 else "-"

                schedule.append({
                    "name": spots[to_node]["name"],
                    "arrival": arrival_time,
                    "departure": departure_time,
                    "tw": tw_str,
                    "stay": stay_str,
                    "arrival_status": arrival_status,
                    "departure_status": departure_status
                })
                current_time = departure_time
            else:
                schedule.append({
                    "name": "酒店（返回）",
                    "arrival": arrival_time,
                    "departure": 0,
                    "tw": "-",
                    "stay": "-",
                    "arrival_status": "",
                    "departure_status": ""
                })
        daily_schedules.append(schedule)

    algo_time = time.time() - total_start
    print("所有任务完成。\n")

    return {
        "solution": solution,
        "mode": mode,
        "best_days": result["best_days"],
        "best_m": result["best_m"],
        "spots": spots,
        "dataset_name": dataset_name,
        "algo_time": algo_time,
        "daily_schedules": daily_schedules,
        "cost_matrix": cost_matrix.tolist(),
        "dist_matrix": dist_matrix.tolist(),
    }


def adjust_plan(spots_dict, cost_matrix_list, dist_matrix_list, routes, adjustments):
    """
    对已有方案执行调整（均衡、重算天数、重算某天）。

    从 routes 重构分组 → 按 adjustments 调整 → 重新求解 → 生成新每日行程。

    Args:
        spots_dict: 景点字典（与 run_planning 返回的 spots 格式一致）。
        cost_matrix_list: 成本矩阵（2D list，前端传回）。
        dist_matrix_list: 距离矩阵（2D list，前端传回）。
        routes: 当前方案路径列表，每组含首尾 depot。
        adjustments: 调整指令 dict，如 {"balance": true}。

    Returns:
        dict: 与 run_planning 相同格式的完整规划结果。
    """
    cost_matrix = np.array(cost_matrix_list)
    dist_matrix = np.array(dist_matrix_list)
    core_groups = [r[1:-1] if len(r) > 2 and r[0] == 0 else r for r in routes]

    if adjustments.get("balance"):
        balanced = balance_groups(core_groups, spots_dict)
        core_groups = [g[1:-1] for g in balanced]

    result = solve_groups(
        core_groups, spots_dict, cost_matrix,
        solver_type="CA",
        travel_speed=TRAVEL_SPEED,
    )
    print(f"调整后总成本: {result['total_cost']:.1f}\n")

    daily_schedules = []
    for day_idx, route in enumerate(result["routes"]):
        schedule = []
        current_time = spots_dict[0]["tw"][0]
        for i in range(len(route) - 1):
            from_node = route[i]
            to_node = route[i + 1]
            travel_time = dist_matrix[from_node][to_node]
            arrival_time = round(current_time + travel_time)

            if to_node != 0:
                original_start, original_end = spots_dict[to_node]["original_tw"]
                effective_start, effective_end = spots_dict[to_node]["tw"]
                stay = spots_dict[to_node]["stay"]

                wait_time = max(0, effective_start - arrival_time)
                late_arrival = max(0, arrival_time - effective_end)
                actual_start = max(arrival_time, effective_start)
                departure_time = actual_start + stay
                late_departure = max(0, departure_time - original_end)

                if int(late_arrival) > 0:
                    arrival_status = f"迟到 {int(late_arrival)} 分钟"
                elif int(wait_time) > 0:
                    arrival_status = f"早到 {int(wait_time)} 分钟"
                else:
                    arrival_status = "正常到达"

                if int(late_departure) > 0:
                    departure_status = f"迟到 {int(late_departure)} 分钟离开"
                else:
                    departure_status = "正常离开"

                tw_str = f"{int(original_start // 60):02d}:{int(original_start % 60):02d} - {int(original_end // 60):02d}:{int(original_end % 60):02d}"
                stay_str = f"{stay} min" if stay > 0 else "-"

                schedule.append({
                    "name": spots_dict[to_node]["name"],
                    "arrival": arrival_time,
                    "departure": departure_time,
                    "tw": tw_str,
                    "stay": stay_str,
                    "arrival_status": arrival_status,
                    "departure_status": departure_status,
                })
                current_time = departure_time
            else:
                schedule.append({
                    "name": "酒店（返回）",
                    "arrival": arrival_time,
                    "departure": 0,
                    "tw": "-",
                    "stay": "-",
                    "arrival_status": "",
                    "departure_status": "",
                })
        daily_schedules.append(schedule)

    return {
        "solution": result,
        "mode": "adjust",
        "best_days": len(routes),
        "best_m": "balance",
        "spots": spots_dict,
        "dataset_name": "调整方案",
        "algo_time": 0,
        "daily_schedules": daily_schedules,
        "cost_matrix": cost_matrix.tolist(),
        "dist_matrix": dist_matrix.tolist(),
    }
