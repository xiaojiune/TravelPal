"""高德地图外部适配：POI 搜索、驾车路径规划、成本矩阵构建（DrivingDataProvider 实现）。

external/<provider>/ 按外部服务分组——未来接入步行/公交等新数据源时，新增
external/walk/、external/bus/ 即可，域层端口（domain/ports）不变。
"""

from backend.infrastructure.external.amap.amap_loader import build_real_data, get_poi_details
from backend.infrastructure.external.amap.driving_service import AmapDrivingProvider, get_matrix, get_pair

__all__ = [
    "build_real_data",
    "get_poi_details",
    "AmapDrivingProvider",
    "get_matrix",
    "get_pair",
]
