"""LangGraph 编排器：单 Agent 中央编排（Router-Executor）。

用 LangGraph StateGraph 管理「LLM 决策 → 工具执行 → 回填 → 再决策」的循环：

- agent 节点：调 LLMService.complete 检测工具调用；无工具调用时用 stream 实时输出最终回复
- tools 节点：按 TOOL_REGISTRY 分发执行工具，结果回填为 tool 消息
- 条件边：有工具调用 → tools 节点；否则 → 结束（多轮串行工具调用由图自环表达）

SSE 事件通过 LangGraph custom stream（StreamWriter）推送给调用方，事件协议：
- ("content", token)    → SSE content 事件（逐 token 实时推送）
- ("tool_status", name) → SSE tool_status 事件
- ("tool_result", data) → SSE tool_result 事件

设计原则：只依赖 langgraph（含 langchain-core），LLM 调用始终走 domain/LLMService
防腐层，不引入 langchain 主包 / langchain-openai——编排框架只管控制流，模型层可插拔。
"""

import inspect
import json
from collections.abc import AsyncIterator
from typing import TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from backend.agent.prompts import TOOL_DEFINITIONS
from backend.agent.tools import TOOL_REGISTRY
from backend.domain.llm_service import ToolCallResult
from backend.infrastructure.llm.factory import get_llm_service

# 模块级复用 LLM client 实例（连接池复用）；factory 切换实现时重建本模块即可
_llm = get_llm_service()


class OrchestratorState(TypedDict):
    """编排图状态。

    Attributes:
        messages: OpenAI 兼容消息列表（system/user/assistant/tool）。
        pending_tool_calls: 待执行的工具调用（agent 节点产出，tools 节点消费）。
    """

    messages: list[dict]
    pending_tool_calls: list[ToolCallResult]


async def _agent_node(state: OrchestratorState) -> dict:
    """LLM 决策节点：检测工具调用，无工具调用时流式输出最终回复。

    Args:
        state: 当前图状态。

    Returns:
        更新后的 messages 与 pending_tool_calls；无工具调用时通过
        StreamWriter 实时推送 content 事件。
    """
    messages = list(state["messages"])
    result = await _llm.complete(messages, tools=TOOL_DEFINITIONS, temperature=0.7, max_tokens=1024)
    if result.tool_calls:
        messages.append(result.message)
        return {"messages": messages, "pending_tool_calls": result.tool_calls}

    writer = get_stream_writer()
    parts: list[str] = []
    async for token in _llm.stream(messages, temperature=0.7, max_tokens=1024):
        parts.append(token)
        writer(("content", token))
    messages.append({"role": "assistant", "content": "".join(parts)})
    return {"messages": messages, "pending_tool_calls": []}


async def _tools_node(state: OrchestratorState) -> dict:
    """工具执行节点：按 TOOL_REGISTRY 分发，结果回填为 tool 消息。

    Args:
        state: 当前图状态（含待执行工具调用）。

    Returns:
        回填工具结果后的 messages 与清空的 pending_tool_calls；
        执行过程通过 StreamWriter 推送 tool_status / tool_result 事件。
    """
    writer = get_stream_writer()
    messages = list(state["messages"])
    for tc in state["pending_tool_calls"]:
        tool_fn = TOOL_REGISTRY.get(tc.name)
        if tool_fn is None:
            continue
        writer(("tool_status", tc.name))
        if inspect.iscoroutinefunction(tool_fn):
            tool_result = await tool_fn(**tc.arguments)
        else:
            tool_result = tool_fn(**tc.arguments)
        writer(("tool_result", tool_result))
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(tool_result, ensure_ascii=False),
            }
        )
    return {"messages": messages, "pending_tool_calls": []}


def _route_after_agent(state: OrchestratorState) -> str:
    """条件路由：有待执行工具 → tools 节点，否则结束。

    Args:
        state: 当前图状态。

    Returns:
        "tools"（继续执行工具）或 "end"（结束编排）。
    """
    return "tools" if state["pending_tool_calls"] else "end"


def _build_graph():
    """构建并编译编排图。"""
    builder = StateGraph(OrchestratorState)
    builder.add_node("agent", _agent_node)
    builder.add_node("tools", _tools_node)
    builder.add_edge(START, "agent")
    builder.add_edge("tools", "agent")
    builder.add_conditional_edges("agent", _route_after_agent, {"tools": "tools", "end": END})
    return builder.compile()


_graph = _build_graph()


async def stream_orchestrator(messages: list[dict]) -> AsyncIterator[tuple]:
    """运行编排器，产出 (event_type, data) 事件流。

    Args:
        messages: OpenAI 兼容消息列表（初始 system/user 消息）。

    Yields:
        (event_type, data) 元组，event_type 为 content / tool_status / tool_result。
    """
    state: OrchestratorState = {"messages": list(messages), "pending_tool_calls": []}
    async for mode, payload in _graph.astream(state, stream_mode="custom"):
        yield mode, payload
