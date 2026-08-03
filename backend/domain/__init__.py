"""领域层：防腐层接口定义。

只声明业务所需的抽象接口（Protocol），不依赖任何具体框架（OpenAI/LangChain）。
实现放在 infrastructure/ 下，通过 factory 切换。
"""

from backend.domain.llm_service import LLMResult, LLMService, ToolCallResult
from backend.domain.weather_service import WeatherInfo, WeatherService

__all__ = [
    "LLMService",
    "LLMResult",
    "ToolCallResult",
    "WeatherService",
    "WeatherInfo",
]
