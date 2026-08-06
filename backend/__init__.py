"""后端包入口（架构导航）。

分层详解见 [`docs/structure/backend.md`](../docs/structure/backend.md)，
系统总览与 C4 架构图见根目录 [`ARCHITECTURE.md`](../ARCHITECTURE.md)。

本包无模块级导出：各子包（api/agent/engine/data/mcp/tasks/...）自带
__init__.py 维护 __all__，公开接口以 import 行为唯一事实来源。
"""
