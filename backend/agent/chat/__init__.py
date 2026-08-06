"""对话链路子包：LangGraph 单 Agent 编排 + 对话消息组装。

消费方：api/routes.py（HTTP 对话端点）。
编排（orchestrator）依赖 agent/tools 的 TOOL_REGISTRY 分发叶子工具。
"""

from backend.agent.chat.chat import build_chat_messages
from backend.agent.chat.orchestrator import stream_orchestrator

__all__ = [
    "build_chat_messages",
    "stream_orchestrator",
]
