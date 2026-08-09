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

from backend.agent.tools import TOOL_REGISTRY
from backend.agent.tools.schema import build_tool_definitions
from backend.domain.llm_service import ToolCallResult
from backend.infrastructure.llm.factory import get_llm_service

# 模块级复用 LLM client 实例（连接池复用）；factory 切换实现时重建本模块即可
_llm = get_llm_service()


class OrchestratorState(TypedDict):
    """编排图状态。

    Attributes:
        messages: OpenAI 兼容消息列表（system/user/assistant/tool）。
        pending_tool_calls: 待执行的工具调用（agent 节点产出，tools 节点消费）。
        tools: 本次会话暴露的工具 schema（按 category 裁剪后，agent 节点据此决策）。
        plan_result: 当前方案快照（PlanResult，可选）。用户进入方案修改场景时由
            前端透传，工具执行时注入给声明 plan 参数的函数（如 add_poi）。
        form_context: 首页表单输入快照（可选）。前端透传，工具执行时注入给声明
            form_context 参数的函数（如 submit_plan_form，据此构造规划请求）。
    """

    messages: list[dict]
    pending_tool_calls: list[ToolCallResult]
    tools: list[dict]
    plan_result: dict | None
    form_context: dict | None


async def _agent_node(state: OrchestratorState) -> dict:
    """LLM 决策节点：检测工具调用，无工具调用时流式输出最终回复。

    Args:
        state: 当前图状态（含裁剪后的 tools schema）。

    Returns:
        更新后的 messages 与 pending_tool_calls；无工具调用时通过
        StreamWriter 实时推送 content 事件。
    """
    messages = list(state["messages"])
    result = await _llm.complete(messages, tools=state["tools"], temperature=0.7, max_tokens=1024)
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

    容错：工具调用包 try/except，参数错误等异常不回传传播（不中断整轮对话），
    而是回填 {"error": ...} 让 LLM 看到错误后 ReAct 自我修正重调——
    这是 PydanticAI re-prompt 重试的手写等价实现（ADR-014 场景二）。
    """
    writer = get_stream_writer()
    messages = list(state["messages"])
    for tc in state["pending_tool_calls"]:
        tool_fn = TOOL_REGISTRY.get(tc.name)
        if tool_fn is None:
            continue
        writer(("tool_status", tc.name))
        kwargs = dict(tc.arguments)
        # 方案修改工具（add_poi）需要当前方案快照：编排层注入 plan_result
        plan = state.get("plan_result")
        if plan and "plan" in inspect.signature(tool_fn).parameters and "plan" not in kwargs:
            kwargs["plan"] = plan
        # 表单上下文工具（submit_plan_form）需要首页输入快照：编排层注入 form_context
        form_ctx = state.get("form_context")
        if form_ctx and "form_context" in inspect.signature(tool_fn).parameters and "form_context" not in kwargs:
            kwargs["form_context"] = form_ctx
        try:
            if inspect.iscoroutinefunction(tool_fn):
                tool_result = await tool_fn(**kwargs)
            else:
                tool_result = tool_fn(**kwargs)
        except Exception as e:
            # 参数缺失/类型错误等：回填错误让 LLM 看到后修正重调，不中断整轮
            tool_result = {"error": f"工具 {tc.name} 执行失败: {e}"}
        # SSE tool_result 事件携带工具名 + 结果（前端据此精确判别卡片类型）；
        # 附带 city（取自工具参数），前端据此自动填充首页城市（仅一次）。
        # 回填 LLM 的 tool 消息仅用结果本体（保持消息协议纯净）
        city = kwargs.get("city")
        payload: dict = {"tool": tc.name, "result": tool_result}
        if city:
            payload["city"] = city
        writer(("tool_result", payload))
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


async def stream_orchestrator(
    messages: list[dict],
    categories: set[str] | None = None,
    plan_result: dict | None = None,
    form_context: dict | None = None,
) -> AsyncIterator[tuple]:
    """运行编排器，产出 (event_type, data) 事件流。

    Args:
        messages: OpenAI 兼容消息列表（初始 system/user 消息）。
        categories: 本次会话暴露的工具分类集合（如 {"poi"}）；
            其余分类的工具 schema 不注入 LLM，实现按上下文裁剪工具；
            None 表示暴露全部工具。
        plan_result: 当前方案快照（PlanResult，可选）。用户进入方案修改场景时
            透传，供 add_poi 等方案修改工具注入。
        form_context: 首页表单输入快照（可选）。前端透传，供 submit_plan_form
            等表单上下文工具注入（据此构造规划请求）。

    Yields:
        (event_type, data) 元组，event_type 为 content / tool_status / tool_result。
    """
    state: OrchestratorState = {
        "messages": list(messages),
        "pending_tool_calls": [],
        "tools": build_tool_definitions(categories),
        "plan_result": plan_result,
        "form_context": form_context,
    }
    async for mode, payload in _graph.astream(state, stream_mode="custom"):
        yield mode, payload
