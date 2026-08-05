"""OpenAI 兼容实现：通过 OpenAI SDK 满足 LLMService 协议。

内部使用 DeepSeek（OpenAI 兼容接口）作为默认后端，行为与旧 chat.py 中的
直接调用完全一致：非流式 complete 返回完整消息 + 工具调用，流式 stream 逐 token 产出。
"""

import json
from collections.abc import AsyncIterator

from openai import OpenAI

from backend.config import settings
from backend.domain.llm_service import LLMResult, LLMService, ToolCallResult
from backend.observability import llm_calls, llm_tokens


class OpenAILLMService(LLMService):
    """基于 OpenAI SDK 的 LLMService 实现（DeepSeek OpenAI 兼容接口）。"""

    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)

    async def complete(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str = "auto",
        **kwargs,
    ) -> LLMResult:
        """非流式补全，含工具调用检测。

        Args:
            messages: OpenAI 兼容的 messages 列表。
            tools: 工具定义列表，None 表示不启用工具。
            tool_choice: 工具选择策略，默认 "auto"。
            **kwargs: 透传 temperature、max_tokens 等参数。

        Returns:
            LLMResult: assistant 完整消息 + 解析后的工具调用列表。
        """
        resp = self.client.chat.completions.create(  # pyright: ignore[reportCallIssue, reportArgumentType]
            model=settings.LLM_MODEL,
            messages=messages,  # pyright: ignore[reportArgumentType]
            tools=tools,  # pyright: ignore[reportArgumentType]
            tool_choice=tool_choice,  # pyright: ignore[reportArgumentType]
            **kwargs,
        )
        llm_calls.labels(kind="complete").inc()
        _record_usage("complete", resp)
        choice = resp.choices[0]
        raw_message = choice.message
        message = {
            "role": "assistant",
            "content": raw_message.content,
        }
        tool_calls: list[ToolCallResult] = []
        if raw_message.tool_calls:
            message["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in raw_message.tool_calls
            ]
            for tc in raw_message.tool_calls:
                try:
                    args: dict = json.loads(tc.function.arguments)  # type: ignore[arg-type]
                except Exception:
                    args = {}
                tool_calls.append(
                    ToolCallResult(id=tc.id, name=tc.function.name, arguments=args)  # type: ignore[arg-type]
                )
        return LLMResult(message=message, tool_calls=tool_calls)

    async def stream(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        """流式补全，逐 token 产出内容。

        Args:
            messages: OpenAI 兼容的 messages 列表。
            **kwargs: 透传 temperature、max_tokens 等参数。

        Yields:
            str: 逐 token 的回复内容。
        """
        resp = self.client.chat.completions.create(  # pyright: ignore[reportCallIssue, reportArgumentType]
            model=settings.LLM_MODEL,
            messages=messages,  # pyright: ignore[reportArgumentType]
            stream=True,
            **kwargs,
        )
        llm_calls.labels(kind="stream").inc()
        # 流式响应中 usage 通常仅在最后一个 chunk 携带，取最后非空值计量
        last_usage = None
        for chunk in resp:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content
            usage = getattr(chunk, "usage", None)
            if usage is not None:
                last_usage = usage
        if last_usage is not None:
            llm_tokens.labels(kind="stream", direction="prompt").inc(getattr(last_usage, "prompt_tokens", 0) or 0)
            llm_tokens.labels(kind="stream", direction="completion").inc(
                getattr(last_usage, "completion_tokens", 0) or 0
            )


def _record_usage(kind: str, resp) -> None:
    """记录 LLM 响应的 token 消耗（prompt/completion 分别计量）。

    Args:
        kind: 调用类型（complete / stream / parse_biz_hours）。
        resp: OpenAI 兼容响应对象（含 usage 属性）。

    用法说明：usage 缺失或为 None 时跳过 token 计量（仅调用次数已计）。
    """
    usage = getattr(resp, "usage", None)
    if usage is None:
        return
    prompt = getattr(usage, "prompt_tokens", 0) or 0
    completion = getattr(usage, "completion_tokens", 0) or 0
    if prompt:
        llm_tokens.labels(kind=kind, direction="prompt").inc(prompt)
    if completion:
        llm_tokens.labels(kind=kind, direction="completion").inc(completion)
