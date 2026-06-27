# src/data/__init__.py
#
# ================== 接口清单 ==================
#
# ---- amap_loader.py ----
# get_poi_location(poi_name, city, key=None) -> (lng, lat) | None              查询 POI 坐标
# get_poi_details(poi_name, city, key=None) -> dict | None                     查询 POI 详细信息
# build_real_data(poi_names, city, delay=0.4) -> Tuple                         批量构建真实成本矩阵
# _parse_opentime_to_tw(opentime_str) -> (start_hour, end_hour) | None         解析高德营业时间为时间窗
#
# ---- cesium_utils.py ----
# generate_cesium_html(routes, spots, mode="3d", ...) -> str (HTML)            生成 Cesium 可视化 HTML

from src.data.amap_loader import get_poi_location, get_poi_details, build_real_data, _parse_opentime_to_tw
from src.data.cesium_utils import generate_cesium_html

__all__ = [
    'get_poi_location', 'get_poi_details', 'build_real_data', '_parse_opentime_to_tw',
    'generate_cesium_html',
]
