import time, os, warnings
import numpy as np

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
os.environ["OMP_NUM_THREADS"] = "1"

from src.data.amap_loader import build_real_data
from src.engine.search import cluster_and_solve
from src.data.cesium_utils import generate_cesium_html

TRAVEL_SPEED = 1.0


def run_planning(poi_cache, city, hotel_name,
                 penalty_weight, early_wait_weight, late_return_weight,
                 mode="fast", n_days=None):
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

    dataset_name = f"{city}_{len(poi_names)-1}spots_{result['best_k']}日游"

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

                tw_str = f"{original_start // 60}:{original_start % 60:02d} - {original_end // 60}:{original_end % 60:02d}"
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

    print("🌍 生成 Cesium 3D 地图...")
    cesium_output_dir = os.path.join("frontend", "static", "cesium", "output")
    os.makedirs(cesium_output_dir, exist_ok=True)
    html_path = generate_cesium_html(
        routes=solution["routes"],
        spots=spots,
        polylines=polylines,
        output_dir=cesium_output_dir,
        dataset_name=dataset_name,
        daily_schedules=daily_schedules
    )
    html_url = f"http://localhost:8099/output/travelpal_route.html"

    algo_time = time.time() - total_start
    print("✅ 所有任务完成。\n")

    return {
        "solution": solution,
        "mode": mode,
        "best_days": result["best_days"],
        "best_m": result["best_m"],
        "spots": spots,
        "dataset_name": dataset_name,
        "html_url": html_url,
        "algo_time": algo_time,
        "daily_schedules": daily_schedules,
    }
