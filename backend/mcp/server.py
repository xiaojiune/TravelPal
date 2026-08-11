"""MCP 服务器入口：FastMCP 兼容层，遍历 TOOL_REGISTRY 暴露叶子工具。

运行方式（stdio 传输，供本地 opencode 懒加载接入）：
    python -m backend.mcp.server

外部 AI 助手通过 MCP Client 连接后，可 list_tools 发现工具并 call_tool 调用。
只复用叶子工具（TOOL_REGISTRY），不引用 LangChain 编排层。
"""

import asyncio
import sys

from mcp.server import MCPServer

from backend.agent.tools import TOOL_REGISTRY

__all__ = ["build_server", "main"]


def build_server() -> MCPServer:
    """构建 MCP 服务器，遍历工具注册表动态注册全部叶子工具。

    Returns:
        MCPServer: 已注册全部 TOOL_REGISTRY 工具的 MCP 服务器实例。
    """
    server = MCPServer("travelpal")
    for name, fn in TOOL_REGISTRY.items():
        server.add_tool(fn, name=name)
    return server


async def _run_stdio(server: MCPServer) -> None:
    """在 stdio 传输上运行 MCP 服务器（异步入口）。"""
    await server.run_stdio_async()


def main() -> None:
    """CLI 入口：启动 MCP 服务器，stdio 传输，阻塞运行。"""
    server = build_server()
    asyncio.run(_run_stdio(server))


if __name__ == "__main__":
    sys.exit(main())
