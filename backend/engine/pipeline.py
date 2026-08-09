"""行程规划双阶段编排：数据加载 → 聚类求解 → 每日行程重建。"""

import os
import time
import warnings

import numpy as np

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
os.environ["OMP_NUM_THREADS"] = "1"

from backend.data.amap_loader import _get_driving_data, build_real_data  # noqa: E402
from backend.data.driving_cache import get_driving_matrix, set_driving_matrix  # noqa: E402
from backend.engine.search import cluster_and_solve  # noqa: E402
from backend.typedefs import PlanResult, PoiCache, ScheduleItem, SpotDict  # noqa: E402

# ================== 常量 ==================


def _supplement_polylines(
    routes_list: list[list[list[int]]],
    coords: list[tuple[float, float]],
    polylines: dict[tuple[int, int], str],
) -> None:
    """扫描 routes 涉及的缺失 polyline 段，逐段补调驾车 API。

    build_real_data 中 cost/dist 对称复用但 polyline 不复制，
    此处对 route 需要但 polylines 中缺失的方向单独补调。

    Args:
        routes_list: 所有方案的 route 列表，每项为 [[0, ...], [0, ...]] 格式。
        coords: 坐标列表，与索引一一对应。
        polylines: 已有 polyline 字典，函数会原地追加缺失项。
    """
    needed: set[tuple[int, int]] = set()
    for routes in routes_list:
        for route in routes:
            for i in range(len(route) - 1):
                key = (route[i], route[i + 1])
                if key not in polylines:
                    needed.add(key)

    if not needed:
        return

    print(f"正在补调 {len(needed)} 段缺失 polyline...")
    for f, t in sorted(needed):
        _, _, poly = _get_driving_data(coords[f], coords[t])  # pyright: ignore[reportGeneralTypeIssues]
        if poly:
            polylines[(f, t)] = poly
        time.sleep(0.4)
    print("polyline 补调完成。\n")


# ================== 主入口 ==================


def run_planning(
    poi_cache: PoiCache,
    city: str,
    hotel_name: str,
    penalty_weight: float,
    early_wait_weight: float,
    late_return_weight: float,
    mode: str = "fast",
    n_days: int | None = None,
    day_start: int = 0,
    min_days: int | None = None,
    cost_matrix_override: list[list[float]] | None = None,
    dist_matrix_override: list[list[float]] | None = None,
) -> PlanResult | dict:
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
        dict: type="suggestion"（未指定天数）时含 suggestions、algo_time、cost_matrix、dist_matrix、polylines；
              规划模式时含 solution、best_days、daily_schedules、cost_matrix、dist_matrix、polylines、commentary 等。
    """
    total_start = time.time()

    poi_names = [hotel_name] + [s["name"] for s in poi_cache["spots"]]
    coords = [(poi_cache["hotel"]["lon"], poi_cache["hotel"]["lat"])] + [
        (s["lon"], s["lat"]) for s in poi_cache["spots"]
    ]

    if cost_matrix_override is not None and dist_matrix_override is not None:
        cost_matrix = np.array(cost_matrix_override, dtype=np.float64)
        dist_matrix = np.array(dist_matrix_override, dtype=np.float64)
        polylines = {}
        print("已复用 suggest 阶段成本矩阵，跳过驾车API调用。\n")
    else:
        # 矩阵快照优先：整矩阵 + polylines 同批绑定缓存，命中直接复用（读加速）
        snapshot = get_driving_matrix(city, poi_names, coords)
        if snapshot is not None:
            cost_matrix = np.array(snapshot["cost"], dtype=np.float64)
            dist_matrix = np.array(snapshot["dist"], dtype=np.float64)
            polylines = {(int(k.split("_")[0]), int(k.split("_")[1])): v for k, v in snapshot["polylines"].items()}
            print("已命中驾车矩阵快照缓存，跳过驾车API调用。\n")
        else:
            print("正在调用驾车API计算成本矩阵...")
            cost_matrix, dist_matrix, polylines = build_real_data(poi_names, coords)
            set_driving_matrix(
                city,
                poi_names,
                coords,
                {
                    "cost": cost_matrix.tolist(),
                    "dist": dist_matrix.tolist(),
                    "polylines": {f"{k[0]}_{k[1]}": v for k, v in polylines.items()},
                },
            )
            print("成本矩阵构建完成，已写入快照缓存。\n")

    hotel_tw = poi_cache["hotel"]["tw"]
    effective_hotel_start = max(hotel_tw[0], day_start)
    spots: dict[int, SpotDict] = {
        0: {
            "name": hotel_name,
            "tw": (effective_hotel_start, hotel_tw[1]),
            "stay": 0,
            "x": poi_cache["hotel"]["lon"],
            "y": poi_cache["hotel"]["lat"],
            "original_tw": hotel_tw,
        }
    }
    for i, spot in enumerate(poi_cache["spots"], start=1):
        tw_start = spot["tw"][0]
        tw_end = spot["tw"][1]
        # 将时间窗收缩为实际可用时段：启程后才有空、到达之后才开放、关闭之前需留足停留时间
        expected_arrival = spot.get("expected_arrival")
        if expected_arrival is None:
            expected_arrival = tw_start
        effective_start = max(tw_start, expected_arrival, day_start)
        effective_end = tw_end - spot["stay"]
        spots[i] = {
            "name": spot["name"],
            "tw": (effective_start, effective_end),
            "original_tw": (tw_start, tw_end),
            "stay": spot["stay"],
            "x": spot["lon"],
            "y": spot["lat"],
        }

    depot = 0

    solve_start = time.time()
    result: PlanResult | dict = cluster_and_solve(
        spots,
        depot,
        cost_matrix,
        mode=mode,
        n_days=n_days,
        min_days=min_days,
        penalty_weight=penalty_weight,
        early_wait_weight=early_wait_weight,
        late_return_weight=late_return_weight,
    )
    if result["type"] != "suggestion":
        algo_name = "VNS" if mode == "deep" else "CA"
        print(f"  {algo_name} 算法求解耗时: {time.time() - solve_start:.2f}s")

    # 后处理（按结果类型分两路，polyline 补调 + 序列化 + 行程重建分属各自分支）
    if result["type"] == "suggestion":
        _supplement_polylines(
            [s["routes"] for s in result["suggestions"]],
            coords,
            polylines,
        )
        polylines_serial = {f"{k[0]}_{k[1]}": v for k, v in polylines.items()}
        result["algo_time"] = round(time.time() - total_start, 2)
        print(f"  suggest 阶段总耗时: {result['algo_time']:.2f}s")
        result["spots"] = spots
        for s in result["suggestions"]:
            s["daily_schedules"] = _rebuild_schedule(s["routes"], spots, cost_matrix)
        result["cost_matrix"] = cost_matrix.tolist()
        result["dist_matrix"] = dist_matrix.tolist()
        result["polylines"] = polylines_serial
        return result

    _supplement_polylines([result["solution"]["routes"]], coords, polylines)
    polylines_serial = {f"{k[0]}_{k[1]}": v for k, v in polylines.items()}

    solution = result["solution"]
    print(f"最优总成本 ({mode} 模式): {solution['total_cost']:.1f}\n")

    dataset_name = f"{city}_{len(poi_names) - 1}spots_{result['best_days']}日游"

    daily_schedules = _rebuild_schedule(solution["routes"], spots, cost_matrix)

    algo_time = time.time() - total_start
    print(f"  plan 阶段总耗时 ({mode}): {algo_time:.2f}s")
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
        "polylines": polylines_serial,
        "commentary": None,
    }


# ================== 工具函数 ==================


def _rebuild_schedule(
    routes: list,
    spots_dict: dict[int, SpotDict],
    cost_matrix: np.ndarray,
) -> list[list[ScheduleItem]]:
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
        schedule.append(
            {
                "name": "酒店（出发）",
                "arrival": current_time,
                "departure": current_time,
                "tw": "-",
                "stay": "-",
                "arrival_status": "",
                "departure_status": "",
            }
        )
        for i in range(len(route) - 1):
            from_node = route[i]
            to_node = route[i + 1]
            travel_time = cost_matrix[from_node][to_node]
            arrival_time = round(current_time + travel_time)  # pyright: ignore[reportCallIssue, reportArgumentType]

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

                tw_str = (
                    f"{int(original_start // 60):02d}:{int(original_start % 60):02d}"
                    f" - {int(original_end // 60):02d}:{int(original_end % 60):02d}"
                )
                stay_str = f"{stay} min" if stay > 0 else "-"

                schedule.append(
                    {
                        "name": spots_dict[to_node]["name"],
                        "arrival": arrival_time,
                        "departure": departure_time,
                        "tw": tw_str,
                        "stay": stay_str,
                        "arrival_status": arrival_status,
                        "departure_status": departure_status,
                    }
                )
                current_time = departure_time
            else:
                schedule.append(
                    {
                        "name": "酒店（返回）",
                        "arrival": arrival_time,
                        "departure": 0,
                        "tw": "-",
                        "stay": "-",
                        "arrival_status": "",
                        "departure_status": "",
                    }
                )
        daily_schedules.append(schedule)
    return daily_schedules


# ================== 方案调整 ==================


def adjust_plan(
    spots_dict: dict[int, SpotDict],
    cost_matrix_list: list,
    dist_matrix_list: list,
    routes: list,
    adjustments: dict,
    city: str = "",
) -> PlanResult:
    """
    对已有方案执行调整（移除景点、添加景点）。

    从 routes 重构分组 → 按 adjustments 类型分发 → 重新求解 → 生成新每日行程。
    纯调度：不含评语（generate_commentary 已剥离为 agent-tool，返回 commentary=None）。

    Args:
        spots_dict: 景点字典（与 run_planning 返回的 spots 格式一致）。
        cost_matrix_list: 成本矩阵（2D list，前端传回）。
        dist_matrix_list: 距离矩阵（2D list，前端传回）。
        routes: 当前方案路径列表，每组含首尾 depot。
        adjustments: 调整指令 dict，支持 {"remove_poi": "<poi_name>", "day": <int>}、\
            {"add_poi": {name, lon, lat, tw_start, tw_end, stay}, "day": <int>?} 之一。\
            remove_poi 为单日重排（day 必填）；add_poi 带 day 为单日重排，\
            day 缺失（用户意图未定）时走全局重排（add_poi_to_plan，@placeholder 兜底）。
        city: 所在城市（add_poi 分支驾车数据点对缓存的 key 前缀；其余分支不影响）。

    Returns:
        dict: 与 run_planning 相同格式的完整规划结果。

    Raises:
        ValueError: adjustments 中未识别的指令类型 / 必要字段缺失。
        RuntimeError: 分支未能产出结果（理论不可达，防御性兜底）。
    """
    cost_matrix = np.array(cost_matrix_list)
    dist_matrix = np.array(dist_matrix_list)

    # 键归一化：前端 JSON 快照的 spots 键为字符串（"0"/"1"），统一转 int 键，
    # 保证 add_poi 分支的 max(keys)+1 与后续索引运算契约一致。
    if spots_dict and all(isinstance(k, str) for k in spots_dict.keys()):
        spots_dict = {int(k): v for k, v in spots_dict.items()}

    plan: dict | None = None
    # 返回给前端的矩阵：默认用输入矩阵；add_poi 分支覆盖为含新点的扩展矩阵
    result_cost = cost_matrix
    result_dist = dist_matrix

    if "remove_poi" in adjustments:
        from backend.agent.planning import remove_poi_from_day

        day = adjustments.get("day")
        if day is None:
            raise ValueError("remove_poi 调整必须指定目标天 day（0-indexed）")
        plan = remove_poi_from_day(
            spots_dict,
            cost_matrix,
            dist_matrix,
            routes,
            adjustments["remove_poi"],
            day,
        )
    elif "add_poi" in adjustments:
        from backend.agent.planning import add_poi_to_day
        from backend.data.amap_loader import _get_driving_data
        from backend.data.driving_cache import get_driving_pair, set_driving_pair

        poi = adjustments["add_poi"]
        day = adjustments.get("day")
        poi_point = {"name": poi["name"], "lon": poi["lon"], "lat": poi["lat"]}
        new_idx = max(spots_dict.keys()) + 1
        # 局部副本：不原地污染调用方传入的 spots_dict
        working_spots = dict(spots_dict)
        working_spots[new_idx] = {  # pyright: ignore[reportArgumentType]
            "name": poi["name"],
            "x": poi["lon"],
            "y": poi["lat"],
            "tw": (poi["tw_start"], poi["tw_end"]),
            "original_tw": (poi["tw_start"], poi["tw_end"]),
            "stay": poi["stay"],
        }

        new_n = len(working_spots)
        new_cost = np.full((new_n, new_n), -1, dtype=np.float64)
        new_cost[: new_n - 1, : new_n - 1] = cost_matrix
        new_dist = np.full((new_n, new_n), -1, dtype=np.float64)
        new_dist[: new_n - 1, : new_n - 1] = dist_matrix

        for i, spot in working_spots.items():
            if i == new_idx:
                new_cost[i][i] = 0
                new_dist[i][i] = 0
                continue
            target_point = {"name": spot["name"], "lon": spot["x"], "lat": spot["y"]}
            cached = get_driving_pair(city, poi_point, target_point)
            if cached is not None:
                # 点对缓存命中：复用上次拉取的驾车数据，跳过 API 调用
                new_cost[new_idx][i] = new_cost[i][new_idx] = cached["duration_min"]
                new_dist[new_idx][i] = new_dist[i][new_idx] = cached["distance_km"]
                continue
            d_km, dur, _ = _get_driving_data((poi["lon"], poi["lat"]), (spot["x"], spot["y"]))  # pyright: ignore[reportGeneralTypeIssues]
            if dur is not None:
                data = {
                    "duration_min": round(dur / 60.0, 2),
                    "distance_km": round(d_km, 2),  # pyright: ignore[reportCallIssue, reportArgumentType]
                }
                new_cost[new_idx][i] = new_cost[i][new_idx] = data["duration_min"]
                new_dist[new_idx][i] = new_dist[i][new_idx] = data["distance_km"]
                set_driving_pair(city, poi_point, target_point, data)
            else:
                new_cost[new_idx][i] = new_cost[i][new_idx] = -1
                new_dist[new_idx][i] = new_dist[i][new_idx] = -1
            time.sleep(0.4)

        if day is not None:
            plan = add_poi_to_day(working_spots, new_cost, new_dist, routes, new_idx, day)
        else:
            # 用户意图未定（未指定天）→ 全局重排兜底
            from backend.agent.planning import add_poi_to_plan

            plan = add_poi_to_plan(working_spots, new_cost, new_dist, routes)
        result_cost = new_cost
        result_dist = new_dist
    else:
        raise ValueError(f"未识别的调整指令: {list(adjustments.keys())}")

    if plan is None:
        raise RuntimeError(f"调整指令 {list(adjustments.keys())} 未产出任何结果")

    result = plan["solution"]
    best_days = plan["best_days"]
    best_m = plan["best_m"]
    daily_schedules = plan["daily_schedules"]

    return {  # type: ignore[return-type]
        "solution": result,
        "mode": "adjust",
        "best_days": best_days,
        "best_m": best_m,
        "spots": spots_dict,
        "dataset_name": "调整方案",
        "algo_time": 0,
        "daily_schedules": daily_schedules,
        "cost_matrix": result_cost.tolist(),
        "dist_matrix": result_dist.tolist(),
        "commentary": None,
    }
