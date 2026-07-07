import os, time, datetime
import numpy as np
import requests
from backend.config import AMAP_API_KEY


def get_poi_location(poi_name, city="北京"):
    """
    通过高德地点搜索 API 获取 POI 坐标。

    Args:
        poi_name: 景点名称。
        city: 城市名，默认北京。

    Returns:
        Tuple[float, float]: (经度, 纬度)，失败时返回 (116.4, 39.9)。
    """
    params = {"keywords": poi_name, "city": city, "key": AMAP_API_KEY}
    try:
        resp = requests.get("https://restapi.amap.com/v3/place/text", params=params, timeout=10)
        data = resp.json()
        if data["status"] == "1" and int(data["count"]) > 0:
            loc = data["pois"][0]["location"]
            lon, lat = map(float, loc.split(','))
            return lon, lat
        else:
            print(f"警告：未找到 '{poi_name}'，使用默认坐标")
            return 116.4, 39.9
    except Exception as e:
        print(f"POI请求失败: {e}")
        return 116.4, 39.9


def _parse_date(date_str, year):
    date_str = date_str.replace('日', '').replace('月', '-')
    parts = date_str.split('-')
    if len(parts) == 2:
        month = int(parts[0])
        day = int(parts[1])
        return datetime.date(year, month, day)
    return None


def _parse_opentime_to_tw(opentime_str):
    """
    解析高德营业时间字符串为时间窗元组。

    支持格式：'月-日:时段-时段'（如 "6-1:09:00-22:00"），
    以及跨日期段 '月-日-月-日:时段-时段'。
    仅返回与当天匹配的时段。

    Args:
        opentime_str: 高德 API 返回的营业时间字符串。

    Returns:
        Tuple[int, int] | None: (开始分钟, 结束分钟)，解析失败返回 None。
    """
    if not opentime_str:
        return None
    today = datetime.date.today()
    current_year = today.year
    segments = opentime_str.replace('：', ':').split('；')
    for seg in segments:
        seg = seg.strip()
        if ':' not in seg:
            continue
        date_part, time_part = seg.rsplit(':', 1)
        date_part = date_part.strip()
        time_part = time_part.strip()
        time_match = time_part.split('-')
        if len(time_match) != 2:
            continue
        try:
            h1, m1 = map(int, time_match[0].strip().split(':'))
            h2, m2 = map(int, time_match[1].strip().split(':'))
            start_min = h1 * 60 + m1
            end_min = h2 * 60 + m2
        except:
            continue
        date_part = date_part.replace(' ', '')
        if '-' in date_part:
            date_range = date_part.split('-')
            if len(date_range) == 2:
                try:
                    start_date = _parse_date(date_range[0], current_year)
                    end_date = _parse_date(date_range[1], current_year)
                    if start_date and end_date and start_date <= today <= end_date:
                        return (start_min, end_min)
                except:
                    continue
        else:
            try:
                single_date = _parse_date(date_part, current_year)
                if single_date and single_date == today:
                    return (start_min, end_min)
            except:
                continue
    return None


def get_poi_details(poi_name, city):
    """
    获取 POI 详细信息（坐标 + 营业时间 + 地址）。

    Args:
        poi_name: 景点名称。
        city: 城市名。

    Returns:
        Tuple[float, float, str, str]: (经度, 纬度, 营业时间字符串, 完整地址)。失败返回默认值。
    """
    params = {"keywords": poi_name, "city": city, "key": AMAP_API_KEY, "extensions": "all"}
    try:
        resp = requests.get("https://restapi.amap.com/v3/place/text", params=params, timeout=10)
        data = resp.json()
        if data["status"] == "1" and int(data["count"]) > 0:
            poi = data["pois"][0]
            loc = poi["location"]
            lon, lat = map(float, loc.split(','))
            biz_hours = ""
            if "biz_ext" in poi and "opentime2" in poi["biz_ext"]:
                biz_hours = poi["biz_ext"]["opentime2"]
            pname = poi.get("pname", "")
            cityname = poi.get("cityname", "")
            adname = poi.get("adname", "")
            street = poi.get("address", "")
            full_address = f"{pname}{cityname}{adname}{street}"
            return lon, lat, biz_hours, full_address
        else:
            print(f"\n警告：未找到 '{poi_name}' 的信息，请尝试更换搜索词")
            return 116.4, 39.9, "", ""
    except Exception as e:
        print(f"POI请求失败: {e}")
        return 116.4, 39.9, "", ""


def _get_driving_data(origin, destination, max_retries=3):
    """
    调用高德驾车路径规划 API 获取距离、耗时、轨迹折线。

    Args:
        origin: (经度, 纬度) 起点坐标。
        destination: (经度, 纬度) 终点坐标。
        max_retries: 失败重试次数，默认 3。

    Returns:
        Tuple[float | None, int | None, str | None]: (距离 km, 耗时 秒, 折线字符串)。
    """
    url = "https://restapi.amap.com/v3/direction/driving"
    params = {
        "origin": f"{origin[0]},{origin[1]}",
        "destination": f"{destination[0]},{destination[1]}",
        "key": AMAP_API_KEY,
        "strategy": "32"
    }
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            if data["status"] == "1" and "route" in data and data["route"].get("paths"):
                path = data["route"]["paths"][0]
                distance_km = int(path["distance"]) / 1000.0
                duration = int(path["duration"])
                polyline = ""
                if "steps" in path:
                    all_points = []
                    for step in path["steps"]:
                        step_poly = step.get("polyline", "")
                        if step_poly:
                            all_points.append(step_poly)
                    polyline = ";".join(all_points)
                return distance_km, duration, polyline
            else:
                print(f"驾车API错误: {data.get('info', '未知错误')}, 状态码: {data.get('infocode', '无')}")
                return None, None, None
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"驾车路径规划请求失败 (第{attempt+1}次重试): {e}")
                time.sleep(1)
            else:
                print(f"驾车路径规划请求失败（已重试{max_retries}次）: {e}")
                return None, None, None


def build_real_data(poi_names, coords, delay=0.4):
    """
    调用高德 API 构建完整的驾车成本矩阵。

    利用对称性优化：A→B 与 B→A 使用相同 API 结果填充，减少一半请求量。
    delay 参数用于控制 QPS，避免触发高德 API 限流。

    Args:
        poi_names: POI 名称列表（含酒店）。
        coords: 坐标列表，与 poi_names 一一对应。
        delay: API 调用间隔秒数，默认 0.4（高德 QPS 限制约 2-3 次/秒）。

    Returns:
        Tuple[np.ndarray, np.ndarray, dict]: cost_matrix（分钟）、dist_matrix_km、polylines_dict。
    """
    n = len(poi_names)
    cost = np.zeros((n, n))
    dist = np.zeros((n, n))
    polylines = {}
    print(f"正在调用驾车API计算 {n}x{n} 矩阵...")
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            # 利用对称性：A→B 已请求过则 B→A 直接填入，减少 API 调用量
            if cost[j][i] > 0:
                cost[i][j] = cost[j][i]
                dist[i][j] = dist[j][i]
                polylines[(i, j)] = polylines.get((j, i), "")
                continue
            d_km, dur, poly = _get_driving_data(coords[i], coords[j])
            if dur is not None:
                cost[i][j] = round(dur / 60.0, 2)
                dist[i][j] = round(d_km, 2)
                if poly:
                    polylines[(i, j)] = poly
            else:
                print(f"警告：{i} -> {j} 驾车路径规划失败")
                # -1 标记不可达（分钟级），下游在计算路由时需跳过此类边
                cost[i][j] = -1
                dist[i][j] = -1
            # 每次 API 调用后等待 delay 秒，控制 QPS 避免被高德限流
            time.sleep(delay)
    return cost, dist, polylines
