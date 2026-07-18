"""对话流：SSE 聊天入口，支持 Mock 和 DeepSeek 两种后端。"""

import asyncio
import json
from openai import OpenAI
from backend.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from backend.agent.tools.prompts import CHAT_SYSTEM


def build_chat_messages(message: str, plan_result: dict | None = None) -> list[dict]:
    """构建对话消息列表。

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

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": message},
    ]


async def mock_stream_chat(messages: list[dict]):
    """Mock SSE 流式聊天，模拟 1 条自然回复用于联调。"""
    reply = "今天的安排不错，下午可以去附近的公园走走！"
    for char in reply:
        yield char
        await asyncio.sleep(0.05)


async def stream_chat(messages: list[dict]):
    """真实 DeepSeek SSE 流式聊天。"""
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
    """统一入口：MOCK_MODE=True 时模拟，否则调 DeepSeek。"""
    if MOCK_MODE:
        async for token in mock_stream_chat(messages):
            yield token
    else:
        async for token in stream_chat(messages):
            yield token
