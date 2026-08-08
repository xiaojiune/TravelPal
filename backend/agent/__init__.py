"""LLM Agent 层：对话链路（chat）+ 规划能力（planning）+ 工具包（tools）。

- chat/：LangGraph 单 Agent 编排 + 消息组装（被 api/routes 消费）
- planning/：方案调整（被 engine/pipeline.adjust_plan 消费）+ 评语生成
  （generate_commentary 已剥离为 agent-tool @placeholder，待接入编排）
- tools/：叶子工具与 TOOL_REGISTRY（被编排器与 MCP 旁路共用）
"""

from backend.agent.chat import build_chat_messages
from backend.agent.planning import generate_commentary
from backend.agent.tools import parse_biz_hours

__all__ = [
    "build_chat_messages",
    "generate_commentary",
    "parse_biz_hours",
]
