"""对话流：SSE 聊天入口，支持 Mock 和 DeepSeek 两种后端。"""

import asyncio
import json
import os

from backend.agent.tools.prompts import CHAT_SYSTEM
from backend.domain.llm_service import LLMResult, LLMService
from backend.infrastructure.llm.factory import get_llm_service
from backend.utils.decorators import placeholder

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _readme_core() -> str:
    """读取 README.md 标题 + 核心功能 + 技术栈，作为项目介绍兜底。"""
    path = os.path.join(_PROJECT_ROOT, "README.md")
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        # 取标题 + 核心功能 + 技术栈（约前 130 行）
        core = "".join(lines[:130])
        return f"\n\n## 项目自述（来自 README.md）\n{core[:2000]}"
    except Exception:
        return ""


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

    system += _readme_core()
    try:
        from backend.agent.tools.rag import search_rag

        results = search_rag(message, k=3)
        if results and results[0]["score"] > 5.0:
            ctx = "\n\n".join(f"[{r['source']}#{r['heading']}]\n{r['text']}" for r in results)
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


# 装饰器定义见 backend/utils/decorators.py
# 说明：模拟 SSE 回复，MOCK_MODE=True 时使用，无需 LLM API Key
@placeholder
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


async def stream_chat(messages: list[dict], service: LLMService | None = None):
    """流式聊天，通过 LLMService 接口调用具体实现。

    Args:
        messages: OpenAI-compatible messages 列表。
        service: LLM 服务实现；None 时由工厂按配置获取。

    Yields:
        str: 流式响应的逐 token 内容。
    """
    llm = service or get_llm_service()
    async for token in llm.stream(messages):
        yield token


async def chat_complete(messages: list[dict], service: LLMService | None = None) -> LLMResult:
    """非流式补全，用于 tool_call 检测。

    Args:
        messages: OpenAI-compatible messages 列表。
        service: LLM 服务实现；None 时由工厂按配置获取。

    Returns:
        LLMResult: 完整 assistant 消息 + 工具调用列表。
    """
    from backend.agent.tools.prompts import TOOL_DEFINITIONS

    llm = service or get_llm_service()
    return await llm.complete(
        messages,
        tools=TOOL_DEFINITIONS,
        tool_choice="auto",
        temperature=0.7,
        max_tokens=1024,
    )


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
