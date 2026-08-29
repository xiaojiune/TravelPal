"""领域层：防腐层接口 + 业务用例编排。

两类内容：
- 防腐层接口（Protocol）：LLM 服务、天气服务——编排层只依赖抽象，具体实现由
  infrastructure/ 经 factory 切换（见 llm_service.py / weather_service.py）。
- 业务用例编排：pipeline.py 的行程规划编排（数据加载 → 求解 → 行程重建），
  纯领域编排，依赖 engine（算法）与 data（IO），不触碰 HTTP/api。

依赖方向：domain → engine / infrastructure / data（不依赖 api、agent）。
"""

from backend.domain.llm_service import LLMResult, LLMService, ToolCallResult
from backend.domain.pipeline import adjust_plan, run_planning
from backend.domain.weather_service import WeatherInfo, WeatherService

__all__ = [
    "LLMResult",
    "LLMService",
    "ToolCallResult",
    "WeatherInfo",
    "WeatherService",
    "adjust_plan",
    "run_planning",
]
