"""天气服务 MCP 实现（可选）。

TODO: 待出现真实可用外部 MCP 服务后实现——用 mcp SDK 连接 MCP server，
将结果映射为 WeatherInfo。接口签名见 backend/domain/weather_service.py。
"""

from backend.domain.weather_service import WeatherInfo


class McpWeatherService:
    """基于外部 MCP 服务的天气服务实现（可选，配置切换启用）。"""

    async def get_weather(self, city: str) -> WeatherInfo:
        """查询指定城市的当前天气。

        Args:
            city: 城市名。

        Returns:
            WeatherInfo: 标准化天气数据。

        Raises:
            NotImplementedError: 当前为接口占位，实现待 TODO 填充。
        """
        raise NotImplementedError("McpWeatherService 待实现（见文件级 TODO）")
