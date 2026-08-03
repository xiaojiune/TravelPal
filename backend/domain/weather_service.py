"""天气服务防腐层接口。

定义对外部天气数据源的唯一依赖面。当前实现状态：**接口规范已定，具体实现
（HTTP / MCP）统一用 TODO 占位**，待真实天气需求出现时按需填充。

降级策略（配置级）：HTTP 为基线实现，MCP 按需启用。两个实现返回完全一致的
``WeatherInfo`` 结构，调用方感知不到差别——这是防腐层支持配置切换的前提。
运行时自动降级（主实现失败回退）暂不做：单服务低并发场景下配置级降级足够。

实现见 backend/infrastructure/weather/，由 factory 按配置切换。
"""

from typing import Protocol


class WeatherInfo:
    """标准化天气数据。

    Attributes:
        city: 城市名。
        temperature: 气温（摄氏度）。
        condition: 天气状况描述（如"晴"）。
        humidity: 相对湿度（百分比）。
        wind: 风力描述（如"3级"）。
    """

    def __init__(
        self,
        city: str,
        temperature: float,
        condition: str,
        humidity: float | None = None,
        wind: str | None = None,
    ) -> None:
        self.city = city
        self.temperature = temperature
        self.condition = condition
        self.humidity = humidity
        self.wind = wind


class WeatherService(Protocol):
    """天气服务抽象接口。

    所有实现（HTTP / MCP）必须满足此协议，编排层只依赖它。
    """

    async def get_weather(self, city: str) -> WeatherInfo:
        """查询指定城市的当前天气。

        Args:
            city: 城市名。

        Returns:
            WeatherInfo: 标准化天气数据。
        """
        ...
