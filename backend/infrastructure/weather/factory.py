"""天气服务工厂：按配置返回具体实现，配置级降级策略的落地处。

配置级降级：`WEATHER_TRANSPORT` 决定返回 HTTP 基线实现还是 MCP 实现，
调用方（编排层）只依赖 WeatherService 接口，切换实现零改动。
运行时自动降级（主实现失败回退）不在当前设计内——单服务低并发场景配置级足够。
"""

# WEATHER_TRANSPORT 待 McpWeatherService 实现后启用（见 get_weather_service 内 TODO）
from backend.domain.weather_service import WeatherService
from backend.infrastructure.weather.http_weather_service import HttpWeatherService


def get_weather_service() -> WeatherService:
    """获取当前启用的天气服务实现。

    当前仅 HTTP 基线实现可用（MCP 实现为 TODO 占位），
    故无论 WEATHER_TRANSPORT 取值为何，均返回 HttpWeatherService；
    待 McpWeatherService 实现后，此处按配置切换。

    Returns:
        WeatherService: 具体实现实例（当前为 HttpWeatherService）。
    """
    # TODO: 实现 McpWeatherService 后，支持
    #   if WEATHER_TRANSPORT == "mcp" and _mcp_available():
    #       return McpWeatherService()
    return HttpWeatherService()
