"""行程规划双阶段编排：数据加载 → 聚类求解 → 每日行程重建。"""

import time, os, warnings
import numpy as np

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
os.environ["OMP_NUM_THREADS"] = "1"

from backend.data.amap_loader import build_real_data
from backend.engine.search import cluster_and_solve, balance_groups, solve_groups
from backend.agent.commentator import generate_commentary
from backend.typedefs import PoiCache, SpotDict, PlanResult, ScheduleItem, RouteResult

# ================== 常量 ==================

TRAVEL_SPEED = 1.0

# ================== 主入口 ==================

def run_planning(poi_cache: PoiCache, city: str, hotel_name: str,
                 penalty_weight: float, early_wait_weight: float, late_return_weight: float,
                 mode: str = "fast", n_days: int | None = None,
                 day_start: int = 0, min_days: int | None = None,
                 cost_matrix_override: list[list[float]] | None = None,
                 dist_matrix_override: list[list[float]] | None = None) -> PlanResult | dict:
    """
    双阶段流程编排入口。

    加载真实数据 → 构建景点字典 → 执行 cluster_and_solve → 生成每日行程 → 返回前端可视化数据。

    Args:
        poi_cache: 包含 hotel 和 spots 的缓存数据（由前端/外部传入）。
        city: 城市名，用于高德 API 查询和文件命名。
        hotel_name: 酒店名称。
        penalty_weight: 违规惩罚权重。
        early_wait_weight: 早到等待惩罚权重。
        late_return_weight: 晚归惩罚权重。
        mode: "fast" 或 "deep"。
        n_days: 行程天数（可选），None 时走建议模式。
        day_start: 每天最早出发时间（0-1440），默认 0（午夜）。
        min_days: 建议模式最小搜索天数（默认由引擎自动推断）。
        cost_matrix_override: 复用 suggest 阶段的成本矩阵，传入时跳过驾车 API。
        dist_matrix_override: 与 cost_matrix_override 一同传入的距离矩阵。

    Returns:
        dict: type="suggestion"（未指定天数）或包含 solution、best_days、daily_schedules 等。
    """
    total_start = time.time()

    poi_names = [hotel_name] + [s["name"] for s in poi_cache["spots"]]
    coords = [(poi_cache["hotel"]["lon"], poi_cache["hotel"]["lat"])] + \
             [(s["lon"], s["lat"]) for s in poi_cache["spots"]]

    if cost_matrix_override is not None and dist_matrix_override is not None:
        cost_matrix = np.array(cost_matrix_override, dtype=np.float64)
        dist_matrix = np.array(dist_matrix_override, dtype=np.float64)
        polylines = {}
        print("已复用 suggest 阶段成本矩阵，跳过驾车API调用。\n")
    else:
        print("正在调用驾车API计算成本矩阵...")
        cost_matrix, dist_matrix, polylines = build_real_data(poi_names, coords)
        print("成本矩阵构建完成。\n")

    hotel_tw = poi_cache["hotel"]["tw"]
    effective_hotel_start = max(hotel_tw[0], day_start)
    spots: dict[int, SpotDict] = {0: {"name": hotel_name,
                 "tw": (effective_hotel_start, hotel_tw[1]),
                 "stay": 0,
                 "x": poi_cache["hotel"]["lon"], "y": poi_cache["hotel"]["lat"],
                 "original_tw": hotel_tw}}
    for i, spot in enumerate(poi_cache["spots"], start=1):
        tw_start = spot["tw"][0]
        tw_end = spot["tw"][1]
        # 将时间窗收缩为实际可用时段：启程后才有空、到达之后才开放、关闭之前需留足停留时间
        expected_arrival = spot.get("expected_arrival")
        if expected_arrival is None:
            expected_arrival = tw_start
        effective_start = max(tw_start, expected_arrival, day_start)
        effective_end = tw_end - spot["stay"]
        spots[i] = {"name": spot["name"],
                    "tw": (effective_start, effective_end),
                    "original_tw": (tw_start, tw_end),
                    "stay": spot["stay"],
                    "x": spot["lon"], "y": spot["lat"]}

    depot = 0

    result: PlanResult | dict = cluster_and_solve(
        spots, depot, cost_matrix, mode=mode,
        n_days=n_days, min_days=min_days,
        travel_speed=TRAVEL_SPEED,
        penalty_weight=penalty_weight,
        early_wait_weight=early_wait_weight,
        late_return_weight=late_return_weight,
    )

    if result["type"] == "suggestion":
        result["algo_time"] = round(time.time() - total_start, 2)
        result["spots"] = spots
        for s in result["suggestions"]:
            s["daily_schedules"] = _rebuild_schedule(s["routes"], spots, cost_matrix)
        result["cost_matrix"] = cost_matrix.tolist()
        result["dist_matrix"] = dist_matrix.tolist()
        return result

    solution = result["solution"]
    print(f"最优总成本 ({mode} 模式): {solution['total_cost']:.1f}\n")

    dataset_name = f"{city}_{len(poi_names)-1}spots_{result['best_days']}日游"

    daily_schedules = _rebuild_schedule(solution["routes"], spots, cost_matrix)

    algo_time = time.time() - total_start
    print("所有任务完成。\n")

    commentary = generate_commentary(solution, spots, dist_matrix)

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
        "commentary": commentary,
    }

# ================== 工具函数 ==================

def _rebuild_schedule(routes: list, spots_dict: dict[int, SpotDict], cost_matrix: np.ndarray) -> list[list[ScheduleItem]]:
    """从路径和景点字典重建每日行程表。

    Args:
        routes: 路径列表，每组含首尾 depot (0)。
        spots_dict: 景点字典。
        cost_matrix: 旅行时间矩阵（分钟）。

    Returns:
        list[list[ScheduleItem]]: 每日行程列表。
    """
    daily_schedules = []
    for route in routes:
        schedule = []
        current_time = spots_dict[0]["tw"][0]
        for i in range(len(route) - 1):
            from_node = route[i]
            to_node = route[i + 1]
            travel_time = cost_matrix[from_node][to_node]
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
    return daily_schedules

# ================== 方案调整 ==================

def adjust_plan(spots_dict: dict[int, SpotDict], cost_matrix_list: list, dist_matrix_list: list, routes: list, adjustments: dict) -> PlanResult:
    """
    对已有方案执行调整（均衡、移除景点、改天数）。

    从 routes 重构分组 → 按 adjustments 类型分发 → 重新求解 → 生成新每日行程。

    Args:
        spots_dict: 景点字典（与 run_planning 返回的 spots 格式一致）。
        cost_matrix_list: 成本矩阵（2D list，前端传回）。
        dist_matrix_list: 距离矩阵（2D list，前端传回）。
        routes: 当前方案路径列表，每组含首尾 depot。
        adjustments: 调整指令 dict，支持 {"balance": true}、{"adjust_days": <int>}、{"remove_poi": "<poi_name>"}、{"add_poi": {name, lon, lat, tw_start, tw_end, stay}} 之一。

    Returns:
        dict: 与 run_planning 相同格式的完整规划结果。

    Raises:
        ValueError: adjustments 中未识别的指令类型。
    """
    cost_matrix = np.array(cost_matrix_list)
    dist_matrix = np.array(dist_matrix_list)

    if "adjust_days" in adjustments:
        from backend.agent.planner import adjust_plan_days
        plan = adjust_plan_days(
            spots_dict, cost_matrix, dist_matrix,
            adjustments["adjust_days"],
        )
        daily_schedules = plan["daily_schedules"]
        result = plan["solution"]
        best_days = plan["best_days"]
        best_m = plan["best_m"]
    elif "remove_poi" in adjustments:
        from backend.agent.planner import remove_poi_from_plan
        plan = remove_poi_from_plan(
            spots_dict, cost_matrix, dist_matrix, routes,
            adjustments["remove_poi"],
        )
        daily_schedules = plan["daily_schedules"]
        result = plan["solution"]
        best_days = plan["best_days"]
        best_m = plan["best_m"]
    elif "add_poi" in adjustments:
        from backend.agent.planner import add_poi_to_plan
        from backend.data.amap_loader import _get_driving_data

        poi = adjustments["add_poi"]
        new_idx = max(spots_dict.keys()) + 1
        spots_dict[new_idx] = {
            "name": poi["name"],
            "x": poi["lon"], "y": poi["lat"],
            "tw": (poi["tw_start"], poi["tw_end"]),
            "stay": poi["stay"],
        }

        new_n = len(spots_dict)
        new_cost = np.full((new_n, new_n), -1, dtype=np.float64)
        new_cost[:new_n-1, :new_n-1] = cost_matrix
        new_dist = np.full((new_n, new_n), -1, dtype=np.float64)
        new_dist[:new_n-1, :new_n-1] = dist_matrix

        for i, spot in spots_dict.items():
            if i == new_idx:
                new_cost[i][i] = 0
                new_dist[i][i] = 0
                continue
            d_km, dur, _ = _get_driving_data((poi["lon"], poi["lat"]), (spot["x"], spot["y"]))
            if dur is not None:
                new_cost[new_idx][i] = new_cost[i][new_idx] = round(dur / 60.0, 2)
                new_dist[new_idx][i] = new_dist[i][new_idx] = round(d_km, 2)
            else:
                new_cost[new_idx][i] = new_cost[i][new_idx] = -1
                new_dist[new_idx][i] = new_dist[i][new_idx] = -1
            time.sleep(0.4)

        plan = add_poi_to_plan(spots_dict, new_cost, new_dist, routes)
        daily_schedules = plan["daily_schedules"]
        result = plan["solution"]
        best_days = plan["best_days"]
        best_m = "add_poi"
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
        daily_schedules = _rebuild_schedule(result["routes"], spots_dict, cost_matrix)
        best_days = len(routes)
        best_m = "balance"

    commentary = generate_commentary(result, spots_dict, dist_matrix)

    return {
        "solution": result,
        "mode": "adjust",
        "best_days": best_days,
        "best_m": best_m,
        "spots": spots_dict,
        "dataset_name": "调整方案",
        "algo_time": 0,
        "daily_schedules": daily_schedules,
        "cost_matrix": cost_matrix.tolist(),
        "dist_matrix": dist_matrix.tolist(),
        "commentary": commentary,
    }
