"""对话流：SSE 聊天入口，支持 Mock 和 DeepSeek 两种后端。"""

import asyncio
import json

from openai import OpenAI

from backend.agent.tools.prompts import CHAT_SYSTEM
from backend.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


def build_chat_messages(message: str, plan_result: dict | None = None) -> list[dict]:
    """构建对话消息列表，自动注入 RAG 文档上下文。

    Args:
        message: 用户输入的消息。
        plan_result: 可选的规划结果，注入 system prompt 作为上下文。

    Returns:
        OpenAI-compatible messages 列表。
    """
    system = CHAT_SYSTEM
    if plan_result:
        summary = {
            "city": plan_result.get("city", "未知"),
            "n_days": plan_result.get("best_days", 0),
            "total_cost": plan_result.get("solution", {}).get("total_cost", 0),
            "commentary": plan_result.get("commentary", ""),
        }
        system += f"\n\n当前规划概要（供参考）：\n{json.dumps(summary, ensure_ascii=False)}"

    try:
        from backend.agent.tools.rag import search_rag
        results = search_rag(message, k=5)
        if results:
            ctx = "\n\n".join(
                f"[{r['source']}#{r['heading']}]\n{r['text']}"
                for r in results
            )
            system += (
                "\n\n以下片段来自项目文档，请优先使用这些信息回答用户关于项目本身的问题。"
                f"引用时标注来源，如 [来源: 技术栈总览]。\n{ctx}"
            )
    except Exception:
        pass

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": message},
    ]


async def mock_stream_chat(messages: list[dict]):
    """调试用：MOCK_MODE=True 时模拟 SSE 流式回复，无需 LLM API Key。

    Args:
        messages: OpenAI-compatible messages 列表。

    Yields:
        str: 模拟回复的逐字符 token。
    """
    reply = "今天的安排不错，下午可以去附近的公园走走！"
    for char in reply:
        yield char
        await asyncio.sleep(0.05)


async def stream_chat(messages: list[dict]):
    """真实 DeepSeek SSE 流式聊天。

    Args:
        messages: OpenAI-compatible messages 列表。

    Yields:
        str: DeepSeek 流式响应的逐 token 内容。
    """
    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        stream=True,
        temperature=0.7,
        max_tokens=1024,
    )
    for chunk in resp:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta and delta.content:
            yield delta.content
            await asyncio.sleep(0)


MOCK_MODE = False


async def chat_stream(messages: list[dict]):
    """统一入口：MOCK_MODE=True 时模拟，否则调 DeepSeek。

    Args:
        messages: OpenAI-compatible messages 列表。

    Yields:
        str: 流式响应的逐 token 内容。
    """
    if MOCK_MODE:
        async for token in mock_stream_chat(messages):
            yield token
    else:
        async for token in stream_chat(messages):
            yield token
