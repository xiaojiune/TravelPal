"""mcp 层契约测试：锁定 MCP Server 工具暴露契约。

ADR-010 #7（契约测试）：纯单元验证 backend/mcp/server.py 的 build_server()
与 TOOL_REGISTRY 保持一致的契约，防止工具注册演进时静默破坏外部 MCP 客户端：
- list_tools 工具名集合 == TOOL_REGISTRY.keys()（单一事实来源）
- 每工具含 name/description/input_schema（schema 从函数注解自动生成）
- call_tool 能调工具函数（add_poi 缺 plan 返回 error，纯单元不触网）

不依赖外部服务（stdio 传输本身不起，直接调 MCPServer 实例方法）。
"""

import asyncio
import json

from backend.agent.tools import TOOL_REGISTRY
from backend.mcp.server import build_server


def _list_tools():
    async def _run():
        server = build_server()
        return await server.list_tools()

    return asyncio.run(_run())


class TestMCPRegistryContract:
    """工具注册契约：MCP 暴露 = TOOL_REGISTRY 单一事实来源。"""

    def test_tool_names_match_registry(self):
        tools = _list_tools()
        names = {t.name for t in tools}
        assert names == set(TOOL_REGISTRY.keys())
        assert len(names) == 6

    def test_every_tool_has_schema_and_description(self):
        tools = _list_tools()
        for t in tools:
            assert t.description, f"{t.name} 缺 description"
            schema = t.input_schema
            assert schema.get("type") == "object"
            assert "properties" in schema

    def test_poi_lookup_schema_required(self):
        tools = _list_tools()
        poi = next(t for t in tools if t.name == "poi_lookup")
        assert set(poi.input_schema.get("required", [])) == {"city", "names"}

    def test_add_poi_day_optional(self):
        """add_poi 的 day 参数可选（缺失=意图未定走全局重排）。"""
        tools = _list_tools()
        add = next(t for t in tools if t.name == "add_poi")
        required = set(add.input_schema.get("required", []))
        assert required == {"city", "poi"}
        assert "day" not in required


class TestMCPCallToolContract:
    """工具调用契约（纯单元，不触网）。"""

    def test_add_poi_missing_plan_returns_error(self):
        async def _run():
            server = build_server()
            return await server.call_tool("add_poi", {"city": "广州", "poi": {"name": "白云山"}})

        result = asyncio.run(_run())
        # call_tool 返回 content 列表，TextContent.text 为 JSON 字符串
        text = result.content[0].text
        payload = json.loads(text)
        assert "error" in payload
