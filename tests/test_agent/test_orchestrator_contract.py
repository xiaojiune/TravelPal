"""编排器契约测试：锁定 LangGraph 单 Agent 编排的 SSE 事件协议与工具裁剪行为。

ADR-010 #7（契约测试）：用可编程 fake LLMService 验证 stream_orchestrator 产出的事件
序列与形状，防止编排层重构（LangGraph 版本/节点调整）时静默破坏对话链路协议：
- 纯聊天 → 仅 content 事件
- 工具调用 → tool_status → tool_result → content 的顺序契约
- category 裁剪 → 注入 LLM 的 tools schema 只含指定分类

fake 走 domain/LLMService 协议（complete/stream），与真实实现解耦，
不依赖外部服务（纯单元测试）。
"""

import asyncio

from backend.agent.chat import orchestrator
from backend.domain.llm_service import LLMResult, ToolCallResult


async def _fake_poi_lookup(city: str, names: list[str]) -> list[dict]:
    """测试用 poi_lookup：直接返回结构化结果，不触网。"""
    return [{"name": names[0], "lon": 113.3, "lat": 23.1, "poi_type": "spot"}]


class _FakeLLM:
    """可编程 fake LLMService：按预设 responses 队列依次响应 complete 调用。

    - ("tool", [ToolCallResult...])：本轮返回工具调用，触发 tools 节点
    - ("text",)：本轮无工具调用，走 stream 输出最终回复
    """

    def __init__(self, responses: list) -> None:
        self.responses = list(responses)
        self.seen_tools: list[list[dict] | None] = []

    async def complete(self, messages: list[dict], tools: list[dict] | None = None, **kwargs) -> LLMResult:
        self.seen_tools.append(tools)
        stage = self.responses.pop(0)
        if stage[0] == "tool":
            tcs = stage[1]
            return LLMResult(message={"role": "assistant", "content": None}, tool_calls=tcs)
        return LLMResult(message={"role": "assistant", "content": ""})

    async def stream(self, messages: list[dict], **kwargs):
        for token in ["你", "好", "呀"]:
            yield token


class TestOrchestratorContract:
    """编排器事件协议契约测试。"""

    def test_pure_chat_only_content_events(self, monkeypatch):
        """纯聊天：无工具调用时只产出 content 事件。"""

        async def run():
            fake = _FakeLLM([("text",)])
            monkeypatch.setattr(orchestrator, "_llm", fake)
            events = []
            async for ev in orchestrator.stream_orchestrator([{"role": "user", "content": "hi"}]):
                events.append(ev)
            return events, fake

        events, _ = asyncio.run(run())
        kinds = [k for k, _ in events]
        assert kinds and all(k == "content" for k in kinds)
        assert "".join(d for _, d in events) == "你好呀"

    def test_tool_call_event_contract(self, monkeypatch):
        """工具调用：事件顺序为 tool_status → tool_result → content（多轮自环）。"""

        async def run():
            fake = _FakeLLM(
                [
                    (
                        "tool",
                        [
                            ToolCallResult(
                                id="call_1",
                                name="poi_lookup",
                                arguments={"city": "广州", "names": ["广州塔"]},
                            )
                        ],
                    ),
                    ("text",),
                ]
            )
            monkeypatch.setattr(orchestrator, "_llm", fake)
            monkeypatch.setattr(orchestrator, "TOOL_REGISTRY", {"poi_lookup": _fake_poi_lookup})
            events = []
            async for ev in orchestrator.stream_orchestrator([{"role": "user", "content": "广州塔在哪"}]):
                events.append(ev)
            return events

        events = asyncio.run(run())
        assert events[0] == ("tool_status", "poi_lookup")
        assert events[1][0] == "tool_result"
        # 结构化协议：携带工具名 + 结果本体
        assert events[1][1]["tool"] == "poi_lookup"
        assert events[1][1]["result"] == [{"name": "广州塔", "lon": 113.3, "lat": 23.1, "poi_type": "spot"}]
        assert all(k == "content" for k, _ in events[2:])
        assert "".join(d for _, d in events[2:]) == "你好呀"

    def test_form_context_injected_to_submit_plan_form(self, monkeypatch):
        """form_context 注入：submit_plan_form 收到编排层注入的表单快照。"""

        captured: dict = {}

        async def fake_submit_plan_form(form_context: dict | None = None, **kwargs) -> dict:
            captured["form_context"] = form_context
            return {"task_id": "t-1", "status": "pending"}

        async def run():
            fake = _FakeLLM(
                [
                    (
                        "tool",
                        [
                            ToolCallResult(
                                id="call_1",
                                name="submit_plan_form",
                                arguments={},
                            )
                        ],
                    ),
                    ("text",),
                ]
            )
            monkeypatch.setattr(orchestrator, "_llm", fake)
            monkeypatch.setattr(
                orchestrator, "TOOL_REGISTRY", {"submit_plan_form": fake_submit_plan_form}
            )
            form_context = {"city": "广州", "hotel_name": "广州塔酒店", "spots": [{"name": "白云山"}]}
            events = []
            async for ev in orchestrator.stream_orchestrator(
                [{"role": "user", "content": "规划一下"}], form_context=form_context
            ):
                events.append(ev)
            return events

        asyncio.run(run())
        # 编排层把 form_context 注入到声明该参数的函数（LLM 无需拼参数）
        assert captured["form_context"] == {"city": "广州", "hotel_name": "广州塔酒店", "spots": [{"name": "白云山"}]}

    def test_tool_exception_does_not_abort(self, monkeypatch):
        """容错：工具执行抛异常时回填 error 让 LLM 修正重调，不中断整轮对话。

        ADR-014 场景二（PydanticAI re-prompt 手写等价）契约：_tools_node
        对工具调用包 try/except，异常转为 {"error": ...} 回填 tool 消息。
        """

        async def _broken_poi_lookup(city: str, names: list[str]) -> list[dict]:
            raise TypeError("参数类型错误")

        async def run():
            fake = _FakeLLM(
                [
                    (
                        "tool",
                        [
                            ToolCallResult(
                                id="call_1",
                                name="poi_lookup",
                                arguments={"city": "广州", "names": "广州塔"},  # names 应为 list → 工具抛 TypeError
                            )
                        ],
                    ),
                    ("text",),
                ]
            )
            monkeypatch.setattr(orchestrator, "_llm", fake)
            monkeypatch.setattr(orchestrator, "TOOL_REGISTRY", {"poi_lookup": _broken_poi_lookup})
            events = []
            async for ev in orchestrator.stream_orchestrator([{"role": "user", "content": "广州塔在哪"}]):
                events.append(ev)
            return events

        events = asyncio.run(run())
        # 工具调用仍产出 tool_status → tool_result（含 error），不抛异常中断
        assert events[0] == ("tool_status", "poi_lookup")
        assert events[1][0] == "tool_result"
        assert events[1][1]["tool"] == "poi_lookup"
        assert "error" in events[1][1]["result"]
        assert "参数类型错误" in events[1][1]["result"]["error"]
        # 错误回填后仍进入 LLM 决策阶段 → content 正常产出，整轮未中断
        assert all(k == "content" for k, _ in events[2:])
        assert "".join(d for _, d in events[2:]) == "你好呀"

    def test_category_pruning(self, monkeypatch):
        """category 裁剪：注入 LLM 的 tools schema 只含指定分类的工具。"""

        async def run(categories: set[str] | None):
            fake = _FakeLLM([("text",)])
            monkeypatch.setattr(orchestrator, "_llm", fake)
            async for _ in orchestrator.stream_orchestrator(
                [{"role": "user", "content": "test"}], categories=categories
            ):
                pass
            return fake

        # 默认全量 7 个工具
        fake_all = asyncio.run(run(None))
        all_names = {d["function"]["name"] for d in fake_all.seen_tools[0]}
        assert all_names == {
            "poi_lookup",
            "get_plan",
            "get_plan_result",
            "get_driving",
            "add_poi",
            "remove_poi",
            "submit_plan_form",
        }

        # 只裁剪出 poi 分类
        fake_poi = asyncio.run(run({"poi"}))
        poi_names = {d["function"]["name"] for d in fake_poi.seen_tools[0]}
        assert poi_names == {"poi_lookup"}

        # 只裁剪出 planning 分类（重工具 + 方案调整 + 表单提交）
        fake_plan = asyncio.run(run({"plan"}))
        plan_names = {d["function"]["name"] for d in fake_plan.seen_tools[0]}
        assert plan_names == {"get_plan", "get_plan_result", "add_poi", "remove_poi", "submit_plan_form"}
