"""天气服务基础设施包。

当前仅落地接口规范与工厂骨架，具体实现（HTTP / MCP）用 TODO 占位——
等真实天气需求出现时按需填充，调用方零改动。
"""

from backend.infrastructure.weather.factory import get_weather_service
from backend.infrastructure.weather.http_weather_service import HttpWeatherService

__all__ = [
    "get_weather_service",
    "HttpWeatherService",
]
