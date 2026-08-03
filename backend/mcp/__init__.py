"""MCP 服务器：将 TravelPal 叶子工具暴露给外部 AI 助手（如 opencode）。

独立进程运行（stdio 传输），遍历 TOOL_REGISTRY 动态注册工具。
只复用叶子工具，不引用 LangChain 编排层；由外部 AI 助手自行判断调用。
"""
