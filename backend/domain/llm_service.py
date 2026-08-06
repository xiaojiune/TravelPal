"""LLM 服务防腐层接口。

定义 Agent 编排层对 LLM 的唯一依赖面：非流式补全（complete）与流式补全（stream）。
使用原生类型（dict / list / str）传递消息与工具参数，禁止任何框架类型
（如 langchain 的 BaseMessage、openai 的 ChatCompletion）泄漏到此接口。

实现见 backend/infrastructure/llm/，由 factory 按需切换。
"""

from collections.abc import AsyncIterator
from typing import Protocol


class ToolCallResult:
    """LLM 返回的一次工具调用指令。

    Attributes:
        id: 工具调用 ID（OpenAI tool_call_id，回填 messages 时使用）。
        name: 工具名。
        arguments: 工具参数（JSON 解析后的 dict，解析失败为 {}）。
    """

    def __init__(self, id: str, name: str, arguments: dict) -> None:
        self.id = id
        self.name = name
        self.arguments = arguments


class LLMResult:
    """非流式补全的标准化结果。

    Attributes:
        message: 完整 assistant 消息（dict，含 role/content，可直接回填 messages）。
        tool_calls: 本次返回的工具调用列表；无工具调用时为空列表。
    """

    def __init__(self, message: dict, tool_calls: list[ToolCallResult] | None = None) -> None:
        self.message = message
        self.tool_calls = tool_calls or []


class LLMService(Protocol):
    """LLM 服务抽象接口。

    所有实现（OpenAI / 未来 LangChain）必须满足此协议，编排层只依赖它。
    """

    async def complete(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str = "auto",
        **kwargs,
    ) -> LLMResult:
        """非流式补全，返回完整消息与可能的工具调用。

        Args:
            messages: OpenAI 兼容的 messages 列表。
            tools: 工具定义列表（JSON Schema 格式），None 表示不启用工具。
            tool_choice: 工具选择策略，默认 "auto"。
            **kwargs: 透传温度、max_tokens 等模型参数。

        Returns:
            LLMResult: 含完整 assistant 消息与工具调用列表。
        """
        ...

    async def stream(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        """流式补全，逐 token 产出内容。

        Args:
            messages: OpenAI 兼容的 messages 列表。
            **kwargs: 透传温度、max_tokens 等模型参数。

        Yields:
            str: 逐 token 的回复内容。
        """
        ...
        yield ""

    async def complete_text(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 128,
        **kwargs,
    ) -> str | None:
        """单轮纯文本补全（无工具调用），返回 assistant 内容。

        供营业时间解析等「纯解析器」子任务复用：只需一段文本输出，
        不需要工具调用检测。调用异常时返回 None（由调用方自行降级）。

        Args:
            prompt: 用户消息文本。
            temperature: 采样温度（解析类任务用低温，默认 0.1）。
            max_tokens: 输出 token 上限（默认 128）。
            **kwargs: 透传其余模型参数。

        Returns:
            str | None: assistant 内容（去首尾空白）；调用异常时返回 None。
        """
        ...
