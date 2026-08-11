"""基础设施层：LLM 服务实现包。"""

from backend.infrastructure.llm.factory import get_llm_service
from backend.infrastructure.llm.openai_impl import OpenAILLMService

__all__ = [
    "get_llm_service",
    "OpenAILLMService",
]
