"""天气服务 HTTP 实现（基线）。

TODO: 待真实天气需求出现后实现——用 httpx 调普通 HTTP API（如和风天气/心知天气），
解析响应为 WeatherInfo。接口签名见 backend/domain/weather_service.py。
"""

from backend.domain.weather_service import WeatherInfo


class HttpWeatherService:
    """基于普通 HTTP API 的天气服务实现（配置基线）。"""

    async def get_weather(self, city: str) -> WeatherInfo:
        """查询指定城市的当前天气。

        Args:
            city: 城市名。

        Returns:
            WeatherInfo: 标准化天气数据。

        Raises:
            NotImplementedError: 当前为接口占位，实现待 TODO 填充。
        """
        raise NotImplementedError("HttpWeatherService 待实现（见文件级 TODO）")
