"""高德地图 API 封装：POI 搜索、营业时间解析、驾车路径规划与成本矩阵构建。"""

import datetime
import re
import time

import numpy as np
import requests

from backend.config import AMAP_API_KEY
from backend.utils.decorators import legacy_only

# ---------- 工具函数 ----------

# 中点符号变体集合（统一归一化为空白后移除）
_MIDDLE_DOTS = set("·・‧•･∙")


def normalize_text(text: str) -> str:
    """全角→半角 + 空白压缩 + 中点符号归一化，用于名称匹配。

    用户输入与高德返回的名称常有空格/中点符号的细微差异，
    归一化后做双向子串匹配，提高酒店/景点名称匹配成功率。
    """
    result = []
    for char in text:
        code = ord(char)
        if char in _MIDDLE_DOTS:
            result.append(" ")
        elif 0xFF01 <= code <= 0xFF5E:
            result.append(chr(code - 0xFEE0))
        else:
            result.append(char)
    return re.sub(r"\s+", "", "".join(result))


def _parse_date(date_str: str, year: int) -> datetime.date | None:
    """解析高德营业时间中的日期段，如 '04月01日' → datetime.date。成功返回 date，失败返回 None。"""
    date_str = date_str.replace("日", "").replace("月", "-")
    parts = date_str.split("-")
    if len(parts) == 2:
        month = int(parts[0])
        day = int(parts[1])
        return datetime.date(year, month, day)
    return None


# ================== 营业时间解析（兜底方案） ==================
# 当前生产环境使用 LLM 解析（tools.poi.py parse_biz_hours），
# 此函数保留用途：
# 1. LLM 解析失败时的 emergency fallback
# 2. 规则解析的参考实现
# 3. 单元测试的对照组（用于对比 LLM 解析的质量）
# 注意：不再维护新格式，仅保持可用状态。
@legacy_only
def _parse_opentime_to_tw(opentime_str: str) -> tuple[int, int] | None:
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
    segments = opentime_str.replace("：", ":").split("；")
    for seg in segments:
        seg = seg.strip()
        if ":" not in seg:
            continue
        date_part, time_part = seg.rsplit(":", 1)
        date_part = date_part.strip()
        time_part = time_part.strip()
        time_match = time_part.split("-")
        if len(time_match) != 2:
            continue
        try:
            h1, m1 = map(int, time_match[0].strip().split(":"))
            h2, m2 = map(int, time_match[1].strip().split(":"))
            start_min = h1 * 60 + m1
            end_min = h2 * 60 + m2
        except Exception:
            continue
        date_part = date_part.replace(" ", "")
        if "-" in date_part:
            date_range = date_part.split("-")
            if len(date_range) == 2:
                try:
                    start_date = _parse_date(date_range[0], current_year)
                    end_date = _parse_date(date_range[1], current_year)
                    if start_date and end_date and start_date <= today <= end_date:
                        return (start_min, end_min)
                except Exception:
                    continue
        else:
            try:
                single_date = _parse_date(date_part, current_year)
                if single_date and single_date == today:
                    return (start_min, end_min)
            except Exception:
                continue
    return None


# ================== POI 详细信息 ==================


def get_poi_details(poi_name: str, city: str) -> tuple[float, float, str, str, str, str, str, str] | str:
    """
    获取 POI 详细信息（坐标 + 营业时间 + 地址 + 省/市名 + 实际名称 + 行业分类）。

    Args:
        poi_name: 景点名称。
        city: 城市名。

    Returns:
        tuple[float, float, str, str, str, str, str, str]: 成功返回 8 元组
        第 8 项 poi_type 为高德行业分类（如 "住宿服务;宾馆酒店"）。
        str: 失败返回错误信息字符串。
    """

    def _match_name(query: str, result_name: str) -> bool:
        """双向子串匹配：归一化全角符号后再比较。"""
        q = normalize_text(query)
        r = normalize_text(result_name)
        return q in r or r in q

    def _extract_poi(poi: dict) -> tuple[float, float, str, str, str, str, str, str]:
        """解析高德 POI 字典，提取坐标/营业时间/地址/行政区划/行业分类。"""
        loc = poi["location"]
        lon, lat = map(float, loc.split(","))
        biz_hours = ""
        if "biz_ext" in poi and "opentime2" in poi["biz_ext"]:
            biz_hours = poi["biz_ext"]["opentime2"]
        pname = poi.get("pname", "")
        cityname = poi.get("cityname", "")
        adname = poi.get("adname", "")
        street = poi.get("address", "")
        full_address = f"{pname}{cityname}{adname}{street}"
        actual_name = poi.get("name", poi_name)
        poi_type = poi.get("type", "")
        return lon, lat, biz_hours, full_address, pname, cityname, actual_name, poi_type

    try:
        # 策略1：types=风景名胜 + city_limit，高德分类准确时直接命中
        params = {
            "keywords": poi_name,
            "city": city,
            "key": AMAP_API_KEY,
            "extensions": "all",
            "city_limit": True,
            "types": "风景名胜",
        }
        resp = requests.get("https://restapi.amap.com/v3/place/text", params=params, timeout=10)
        data = resp.json()
        if data["status"] == "1" and int(data.get("count", 0)) > 0:
            poi = data["pois"][0]
            if _match_name(poi_name, poi.get("name", "")):
                return _extract_poi(poi)

        # 策略2：去掉 types，按关键词相关性自然排序（如岭南印象园→中山纪念堂的误配）
        params2 = {k: v for k, v in params.items() if k != "types"}
        resp2 = requests.get("https://restapi.amap.com/v3/place/text", params=params2, timeout=10)
        data2 = resp2.json()
        if data2["status"] == "1" and int(data2.get("count", 0)) > 0:
            poi2 = data2["pois"][0]
            if _match_name(poi_name, poi2.get("name", "")):
                return _extract_poi(poi2)

        # 策略3：全国搜索，仅用于判定跨城市（city_limit 排除了不在本市的景点）
        relax_params = {k: v for k, v in params2.items() if k != "city_limit"}
        resp3 = requests.get("https://restapi.amap.com/v3/place/text", params=relax_params, timeout=10)
        data3 = resp3.json()
        if data3["status"] == "1" and int(data3.get("count", 0)) > 0:
            poi3 = data3["pois"][0]
            pname = poi3.get("pname", "")
            cityname = poi3.get("cityname", "")
            # 同城市则返回，不限名字（高德全国搜索默认按相关性排序）
            if city and cityname and city in cityname:
                if _match_name(poi_name, poi3.get("name", "")):
                    return _extract_poi(poi3)
                return f"未找到 '{poi_name}' 的信息"
            return f"'{poi_name}' 不在 {city}，可能在 {pname}{cityname}"

        return f"未找到 '{poi_name}' 的信息"
    except Exception as e:
        print(f"POI请求失败: {e}")
        return f"'{poi_name}' 查询失败"


# ================== 驾车路径规划 ==================


def _get_driving_data(origin: tuple[float, float], destination: tuple[float, float], max_retries: int = 3):
    """
    调用高德驾车路径规划 API 获取距离、耗时、轨迹折线。

    Args:
        origin: (经度, 纬度) 起点坐标。
        destination: (经度, 纬度) 终点坐标。
        max_retries: 失败重试次数，默认 3。

    Returns:
        Tuple[float | None, int | None, str | None]: (距离 km, 耗时 秒, 折线字符串)。

    Raises:
        Exception: 网络请求异常时重试，重试耗尽后返回 (None, None, None)。
    """
    url = "https://restapi.amap.com/v3/direction/driving"
    params = {
        "origin": f"{origin[0]},{origin[1]}",
        "destination": f"{destination[0]},{destination[1]}",
        "key": AMAP_API_KEY,
        "strategy": "32",
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
                print(f"驾车路径规划请求失败 (第{attempt + 1}次重试): {e}")
                time.sleep(1)
            else:
                print(f"驾车路径规划请求失败（已重试{max_retries}次）: {e}")
                return None, None, None


# ================== 批量构建成本矩阵 ==================


def build_real_data(poi_names: list[str], coords: list[tuple[float, float]], delay: float = 0.4):
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

    Raises:
        Exception: 驾车 API 调用失败时输出警告，对应矩阵元素置为 -1 标记不可达。
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
            # cost/dist 对称复用，polyline 因方向相关不作对称（由 pipeline._supplement_polylines 补调）
            if cost[j][i] > 0:
                cost[i][j] = cost[j][i]
                dist[i][j] = dist[j][i]
                continue
            result = _get_driving_data(coords[i], coords[j])
            d_km, dur, poly = result if result else (None, None, None)
            if dur is not None and d_km is not None:
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
