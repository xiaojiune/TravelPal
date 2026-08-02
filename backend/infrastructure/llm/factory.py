"""LLM 服务工厂：按配置返回具体实现，切换实现时编排层零改动。"""

from backend.domain.llm_service import LLMService
from backend.infrastructure.llm.openai_impl import OpenAILLMService


def get_llm_service() -> LLMService:
    """获取当前启用的 LLM 服务实现。

    Returns:
        LLMService: 具体实现实例（当前为 OpenAILLMService）。
    """
    return OpenAILLMService()
